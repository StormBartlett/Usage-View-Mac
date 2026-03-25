"""
Floating usage dashboard window using macOS native WKWebView.

Shows Claude, Cursor and Codex dashboards in a tabbed panel.
Log in once — cookies persist in the WKWebView data store.
"""
import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeToggle,
    NSColor,
    NSFont,
    NSMakeRect,
    NSMakeSize,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSURL, NSURLRequest
from WebKit import WKWebView, WKWebViewConfiguration

TABS = [
    ("Claude",  "https://claude.ai/settings/usage"),
    ("Cursor",  "https://cursor.com/dashboard/spending"),
    ("Codex",   "https://chatgpt.com/codex/settings/usage"),
]

# Accent colours per tab (hex R,G,B 0-1)
TAB_COLORS = [
    (0.82, 0.47, 0.29),   # Claude orange
    (0.12, 0.53, 0.90),   # Cursor blue
    (0.21, 0.68, 0.49),   # Codex green
]

_WINDOW: NSWindow | None = None
_WEBVIEW: WKWebView | None = None
_TAB_BUTTONS: list = []
_CURRENT_TAB: int = -1


def show_dashboard(tab_index: int = 0):
    """Open (or focus) the dashboard window and switch to tab_index."""
    _ensure_window()
    _switch_tab(tab_index)

    global _WINDOW
    _WINDOW.makeKeyAndOrderFront_(None)
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _ensure_window():
    global _WINDOW, _WEBVIEW, _TAB_BUTTONS

    if _WINDOW is not None:
        return

    W, H = 1_100, 760
    TAB_H = 44
    PADDING = 8

    style = (
        NSWindowStyleMaskTitled
        | NSWindowStyleMaskClosable
        | NSWindowStyleMaskResizable
        | NSWindowStyleMaskMiniaturizable
    )
    _WINDOW = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(200, 200, W, H),
        style,
        NSBackingStoreBuffered,
        False,
    )
    _WINDOW.setTitle_("Usage Dashboards")
    _WINDOW.setMinSize_(NSMakeSize(700, 500))

    content = _WINDOW.contentView()

    # ---- Tab bar ----
    tab_bar = NSView.alloc().initWithFrame_(
        NSMakeRect(0, H - TAB_H, W, TAB_H)
    )
    tab_bar.setAutoresizingMask_(0b10010)   # flexible width + top margin
    tab_bar.setWantsLayer_(True)
    tab_bar.layer().setBackgroundColor_(
        NSColor.colorWithRed_green_blue_alpha_(0.13, 0.13, 0.13, 1).CGColor()
    )
    content.addSubview_(tab_bar)

    btn_w = (W - PADDING * 2) // len(TABS)
    _TAB_BUTTONS.clear()
    for i, (label, _url) in enumerate(TABS):
        btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(PADDING + i * btn_w, 5, btn_w - PADDING, TAB_H - 10)
        )
        btn.setTitle_(label)
        btn.setButtonType_(NSButtonTypeToggle)
        btn.setBezelStyle_(13)      # rounded rect
        btn.setFont_(NSFont.boldSystemFontOfSize_(13))
        btn.setTag_(i)
        btn.setTarget_(_TabTarget.shared())
        btn.setAction_(objc.selector(
            _TabTarget.shared().buttonClicked_,
            signature=b"v@:@"
        ))
        tab_bar.addSubview_(btn)
        _TAB_BUTTONS.append(btn)

    # ---- WKWebView ----
    cfg = WKWebViewConfiguration.alloc().init()
    _WEBVIEW = WKWebView.alloc().initWithFrame_configuration_(
        NSMakeRect(0, 0, W, H - TAB_H),
        cfg,
    )
    _WEBVIEW.setAutoresizingMask_(0b11010)  # flexible width + height
    content.addSubview_(_WEBVIEW)


def _switch_tab(index: int):
    global _CURRENT_TAB

    if index == _CURRENT_TAB:
        return
    _CURRENT_TAB = index

    # Update button states
    for i, btn in enumerate(_TAB_BUTTONS):
        btn.setState_(1 if i == index else 0)
        r, g, b = TAB_COLORS[i]
        if i == index:
            btn.setContentTintColor_(
                NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1)
            )
        else:
            btn.setContentTintColor_(NSColor.secondaryLabelColor())

    # Load URL
    url_str = TABS[index][1]
    ns_url = NSURL.URLWithString_(url_str)
    _WEBVIEW.loadRequest_(NSURLRequest.requestWithURL_(ns_url))


# ---------------------------------------------------------------------------
# Simple ObjC target for button clicks
# ---------------------------------------------------------------------------

class _TabTarget(NSView):
    _instance = None

    @classmethod
    def shared(cls):
        if cls._instance is None:
            cls._instance = cls.alloc().init()
        return cls._instance

    @objc.python_method
    def _noop(self):
        pass

    def buttonClicked_(self, sender):
        _switch_tab(sender.tag())
