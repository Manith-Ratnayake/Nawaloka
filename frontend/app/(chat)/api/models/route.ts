export async function GET() {
  return Response.json(
    {},
    {
      headers: {
        "Cache-Control": "public, max-age=86400, s-maxage=86400",
      },
    }
  );
}