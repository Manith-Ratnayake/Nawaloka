import { ipAddress } from "@vercel/functions";
import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  generateId,
} from "ai";
import { checkBotId } from "botid/server";
import { after } from "next/server";
import { createResumableStreamContext } from "resumable-stream";
import { auth, type UserType } from "@/app/(auth)/auth";
import { entitlementsByUserType } from "@/lib/ai/entitlements";
import { allowedModelIds, DEFAULT_CHAT_MODEL } from "@/lib/ai/models";
import { callBackend } from "@/lib/backend";
import {
  createStreamId,
  deleteChatById,
  getChatById,
  getMessageCountByUserId,
  getMessagesByChatId,
  saveChat,
  saveMessages,
  updateChatTitleById,
  updateMessage,
} from "@/lib/db/queries";
import type { DBMessage } from "@/lib/db/schema";
import { ChatbotError } from "@/lib/errors";
import { checkIpRateLimit } from "@/lib/ratelimit";
import type { ChatMessage } from "@/lib/types";
import { convertToUIMessages, generateUUID } from "@/lib/utils";
import { generateTitleFromUserMessage } from "../../actions";
import { type PostRequestBody, postRequestBodySchema } from "./schema";

export const maxDuration = 60;

function describeError(error: unknown) {
  if (!(error instanceof Error)) {
    return String(error);
  }

  const cause = error.cause instanceof Error ? ` | Cause: ${error.cause.message}` : "";

  return `${error.name}: ${error.message}${cause}`;
}

function getMessageText(message?: ChatMessage) {
  return (
    message?.parts
      ?.filter((part) => part.type === "text")
      .map((part) => part.text)
      .join(" ")
      .trim() ?? ""
  );
}

function getLatestUserMessageText(messages: ChatMessage[]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const currentMessage = messages[index];

    if (currentMessage.role !== "user") {
      continue;
    }

    const text = getMessageText(currentMessage);

    if (text) {
      return text;
    }
  }

  return "";
}

function getStreamContext() {
  try {
    return createResumableStreamContext({ waitUntil: after });
  } catch {
    return null;
  }
}

export { getStreamContext };

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (error) {
    console.error("REQUEST PARSING ERROR:", error);
    return new ChatbotError("bad_request:api").toResponse();
  }

  try {
    const {
      id,
      message,
      messages,
      selectedChatModel,
      selectedVisibilityType,
    } = requestBody;

    const [botIdResult, session] = await Promise.all([
      checkBotId().catch(() => null),
      auth(),
    ]);

    if (botIdResult?.isBot) {
      return new ChatbotError("forbidden:api").toResponse();
    }

    if (!session?.user) {
      return new ChatbotError("unauthorized:chat").toResponse();
    }

    const chatModel = allowedModelIds.has(selectedChatModel)
      ? selectedChatModel
      : DEFAULT_CHAT_MODEL;

    await checkIpRateLimit(ipAddress(request));

    const userType: UserType = session.user.type;

    const messageCount = await getMessageCountByUserId({
      differenceInHours: 1,
      id: session.user.id,
    });

    if (messageCount > entitlementsByUserType[userType].maxMessagesPerHour) {
      return new ChatbotError("rate_limit:chat").toResponse();
    }

    const isToolApprovalFlow = Boolean(messages);

    const chat = await getChatById({ id });
    let messagesFromDb: DBMessage[] = [];
    let titlePromise: Promise<string> | null = null;

    if (chat) {
      if (chat.userId !== session.user.id) {
        return new ChatbotError("forbidden:chat").toResponse();
      }

      messagesFromDb = await getMessagesByChatId({ id });
    } else if (message?.role === "user") {
      await saveChat({
        id,
        title: "New chat",
        userId: session.user.id,
        visibility: selectedVisibilityType,
      });

      titlePromise = generateTitleFromUserMessage({ message });
    }

    let uiMessages: ChatMessage[];

    if (isToolApprovalFlow && messages) {
      const dbMessages = convertToUIMessages(messagesFromDb);
      const approvalStates = new Map(
        messages.flatMap(
          (currentMessage) =>
            currentMessage.parts
              ?.filter(
                (part: Record<string, unknown>) =>
                  part.state === "approval-responded" ||
                  part.state === "output-denied"
              )
              .map((part: Record<string, unknown>) => [
                String(part.toolCallId ?? ""),
                part,
              ]) ?? []
        )
      );

      uiMessages = dbMessages.map((currentMessage) => ({
        ...currentMessage,
        parts: currentMessage.parts.map((part) => {
          if ("toolCallId" in part && approvalStates.has(String(part.toolCallId))) {
            return { ...part, ...approvalStates.get(String(part.toolCallId)) };
          }

          return part;
        }),
      })) as ChatMessage[];
    } else {
      uiMessages = [
        ...convertToUIMessages(messagesFromDb),
        message as ChatMessage,
      ];
    }

    if (message?.role === "user") {
      await saveMessages({
        messages: [
          {
            attachments: [],
            chatId: id,
            createdAt: new Date(),
            id: message.id,
            parts: message.parts,
            role: "user",
          },
        ],
      });
    }

    const stream = createUIMessageStream({
      execute: async ({ writer: dataStream }) => {
        const userMessage =
          getMessageText(message as ChatMessage | undefined) ||
          getLatestUserMessageText(uiMessages);

        if (!userMessage) {
          throw new Error("No user message was found to send to the backend");
        }

        console.log("RENDER REQUEST:", {
          message: userMessage,
          model: chatModel,
        });

        const backendResponse = await callBackend(userMessage, chatModel);

        console.log("RENDER RESPONSE:", backendResponse);

        if (
          !backendResponse ||
          typeof backendResponse.message !== "string" ||
          !backendResponse.message.trim()
        ) {
          throw new Error(
            "Backend returned an invalid response. Expected { message: string }"
          );
        }

        const textId = generateUUID();

        dataStream.write({
          type: "text-start",
          id: textId,
        });

        dataStream.write({
          type: "text-delta",
          id: textId,
          delta: backendResponse.message,
        });

        dataStream.write({
          type: "text-end",
          id: textId,
        });

        if (titlePromise) {
          try {
            const title = await titlePromise;

            dataStream.write({
              data: title,
              type: "data-chat-title",
            });

            await updateChatTitleById({ chatId: id, title });
          } catch (error) {
            console.error("CHAT TITLE ERROR:", error);
          }
        }
      },
      generateId: generateUUID,
      onEnd: async ({ messages: finishedMessages }) => {
        if (isToolApprovalFlow) {
          await Promise.all(
            finishedMessages.map(async (finishedMessage) => {
              const existingMessage = uiMessages.find(
                (currentMessage) => currentMessage.id === finishedMessage.id
              );

              if (existingMessage) {
                await updateMessage({
                  id: finishedMessage.id,
                  parts: finishedMessage.parts,
                });
                return;
              }

              await saveMessages({
                messages: [
                  {
                    attachments: [],
                    chatId: id,
                    createdAt: new Date(),
                    id: finishedMessage.id,
                    parts: finishedMessage.parts,
                    role: finishedMessage.role,
                  },
                ],
              });
            })
          );
        } else if (finishedMessages.length > 0) {
          await saveMessages({
            messages: finishedMessages.map((currentMessage) => ({
              attachments: [],
              chatId: id,
              createdAt: new Date(),
              id: currentMessage.id,
              parts: currentMessage.parts,
              role: currentMessage.role,
            })),
          });
        }
      },
      onError: (error) => {
        const message = describeError(error);

        console.error("CHAT STREAM ERROR:", error);
        console.error("CHAT STREAM ERROR DESCRIPTION:", message);

        return message;
      },
      originalMessages: isToolApprovalFlow ? uiMessages : undefined,
    });

    return createUIMessageStreamResponse({
      async consumeSseStream({ stream: sseStream }) {
        if (!process.env.REDIS_URL) {
          return;
        }

        try {
          const streamContext = getStreamContext();

          if (streamContext) {
            const streamId = generateId();

            await createStreamId({
              chatId: id,
              streamId,
            });

            await streamContext.createNewResumableStream(
              streamId,
              () => sseStream
            );
          }
        } catch (error) {
          console.error("RESUMABLE STREAM ERROR:", error);
        }
      },
      stream,
    });
  } catch (error) {
    const vercelId = request.headers.get("x-vercel-id");
    const message = describeError(error);

    console.error("UNHANDLED CHAT API ERROR:", error, {
      description: message,
      vercelId,
    });

    if (error instanceof ChatbotError) {
      return error.toResponse();
    }

    return new ChatbotError("offline:chat").toResponse();
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatbotError("bad_request:api").toResponse();
  }

  const session = await auth();

  if (!session?.user) {
    return new ChatbotError("unauthorized:chat").toResponse();
  }

  const chat = await getChatById({ id });

  if (chat?.userId !== session.user.id) {
    return new ChatbotError("forbidden:chat").toResponse();
  }

  const deletedChat = await deleteChatById({ id });

  return Response.json(deletedChat, { status: 200 });
}
