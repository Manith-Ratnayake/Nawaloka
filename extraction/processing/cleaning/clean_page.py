"""Remove page chrome and non-readable interface elements."""

from text import node_text


HEADING_XPATH = ".//h1|.//h2|.//h3|.//h4|.//h5|.//h6"

# A hidden element carrying at least this much readable text is treated as real
# collapsed content (e.g. an accordion / tab / FAQ answer panel) and kept.
# Below it, a hidden node is considered decorative chrome and removed.
MIN_HIDDEN_KEEP_CHARS = 12

STANDARD_NOISE_XPATHS = [
    "//script",
    "//style",
    "//noscript",
    "//template",
    "//header",
    "//footer",
    "//nav",
    "//*[@role='navigation']",
    "//*[@role='banner']",
    "//*[@role='contentinfo']",
]

FORM_XPATHS = ["//form", "//*[@role='form']"]


def remove_element(node):
    parent = node.getparent()
    if parent is not None:
        parent.remove(node)


def remove_site_header(root):
    """Remove the heading-free site header that owns the dropdown navigation."""
    candidates = []

    for node in root.xpath("//div|//section"):
        if len(node.xpath(".//*[@aria-haspopup='menu']")) < 2:
            continue
        if node.xpath(HEADING_XPATH):
            continue

        parent = node.getparent()
        if parent is None or not parent.xpath(HEADING_XPATH):
            continue

        candidates.append(node)

    if candidates:
        header = max(candidates, key=lambda node: len(node.xpath(".//*")))
        remove_element(header)


def remove_standard_noise(root):
    for xpath in STANDARD_NOISE_XPATHS:
        for node in list(root.xpath(xpath)):
            remove_element(node)


def remove_forms(root):
    for xpath in FORM_XPATHS:
        for node in list(root.xpath(xpath)):
            remove_element(node)


def remove_hidden_elements(root):
    """Remove elements the page marks as hidden.

    Collapsed accordion / tab / FAQ panels are commonly marked ``hidden``,
    ``aria-hidden='true'`` or ``display:none`` while still holding real content
    (e.g. FAQ answers). Removing those loses page knowledge, so a hidden node is
    only dropped when it carries no meaningful text. Keeping the occasional
    duplicated or inactive-state block is preferable to silently dropping
    answers, and a later stage can dedupe if needed.
    """
    hidden_nodes = list(root.xpath("//*[@hidden or @aria-hidden='true']"))

    for node in root.xpath("//*[@style]"):
        style = "".join((node.get("style") or "").lower().split())
        if "display:none" in style or "visibility:hidden" in style:
            hidden_nodes.append(node)

    for node in dict.fromkeys(hidden_nodes):
        if len(node_text(node)) >= MIN_HIDDEN_KEEP_CHARS:
            continue
        remove_element(node)


def remove_fixed_ui(root):
    """Remove floating widgets such as chat/help controls without naming them."""
    for node in list(root.xpath("//*[@style]")):
        style = "".join((node.get("style") or "").lower().split())
        if "position:fixed" in style:
            remove_element(node)


def clean_page(root):
    remove_site_header(root)
    remove_standard_noise(root)
    remove_forms(root)
    remove_hidden_elements(root)
    remove_fixed_ui(root)
