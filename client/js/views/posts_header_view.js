"use strict";

const events = require("../events.js");
const settings = require("../models/settings.js");
const keyboard = require("../util/keyboard.js");
const misc = require("../util/misc.js");
const search = require("../util/search.js");
const views = require("../util/views.js");
const TagList = require("../models/tag_list.js");
const TagAutoCompleteControl = require("../controls/tag_auto_complete_control.js");

const template = views.getTemplate("posts-header");

class BulkEditor extends events.EventTarget {
    constructor(hostNode) {
        super();
        this._hostNode = hostNode;
        this._openLinkNode.addEventListener("click", (e) =>
            this._evtOpenLinkClick(e)
        );
        this._closeLinkNode.addEventListener("click", (e) =>
            this._evtCloseLinkClick(e)
        );
    }

    get opened() {
        return (
            this._hostNode.classList.contains("opened") &&
            !this._hostNode.classList.contains("hidden")
        );
    }

    get _openLinkNode() {
        return this._hostNode.querySelector(".open");
    }

    get _closeLinkNode() {
        return this._hostNode.querySelector(".close");
    }

    toggleOpen(state) {
        this._hostNode.classList.toggle("opened", state);
    }

    toggleHide(state) {
        this._hostNode.classList.toggle("hidden", state);
    }

    _evtOpenLinkClick(e) {
        throw new Error("Not implemented");
    }

    _evtCloseLinkClick(e) {
        throw new Error("Not implemented");
    }
}

class BulkSafetyEditor extends BulkEditor {
    _evtOpenLinkClick(e) {
        e.preventDefault();
        this.toggleOpen(true);
        this.dispatchEvent(new CustomEvent("open", { detail: {} }));
    }

    _evtCloseLinkClick(e) {
        e.preventDefault();
        this.toggleOpen(false);
        this.dispatchEvent(new CustomEvent("close", { detail: {} }));
    }
}

class BulkTagEditor extends BulkEditor {
    constructor(hostNode) {
        super(hostNode);
        this._running = false;
        this._autoCompleteControl = new TagAutoCompleteControl(
            this._inputNode,
            {
                confirm: (tag) => {
                    let tag_list = new TagList();
                    tag_list
                        .addByName(tag.names[0], true)
                        .then(
                            () => {
                                return tag_list
                                    .map((s) => s.names[0])
                                    .join(" ");
                            },
                            (err) => {
                                return tag.names[0];
                            }
                        )
                        .then((tag_str) => {
                            this._autoCompleteControl.replaceSelectedText(
                                tag_str,
                                false
                            );
                        });
                },
            }
        );
        this._hostNode.addEventListener("submit", (e) =>
            this._evtFormSubmit(e)
        );
        this._tagAllButtonNode.addEventListener("click", (e) =>
            this._evtTagAllClick(e)
        );
        this._untagAllButtonNode.addEventListener("click", (e) =>
            this._evtUntagAllClick(e)
        );
    }

    get value() {
        return this._inputNode.value;
    }

    get _inputNode() {
        return this._hostNode.querySelector("input[name=tag]");
    }

    get _tagAllButtonNode() {
        return this._hostNode.querySelector(".tag-all");
    }

    get _untagAllButtonNode() {
        return this._hostNode.querySelector(".untag-all");
    }

    get _progressBarNode() {
        return this._hostNode.querySelector(".progress-bar");
    }

    get _progressTextNode() {
        return this._hostNode.querySelector(".progress-text");
    }

    focus() {
        this._inputNode.focus();
    }

    blur() {
        this._autoCompleteControl.hide();
        this._inputNode.blur();
    }

    setRunning(running) {
        this._running = running;
        this._hostNode.classList.toggle("running", running);
        this._closeLinkNode.textContent = running
            ? "Cancel"
            : "Stop tagging";
        if (!running) {
            this.setProgress(0, 0, 0);
        }
    }

    setProgress(processed, total, etaSeconds) {
        this._progressBarNode.max = Math.max(total, 1);
        this._progressBarNode.value = processed;
        this._progressTextNode.textContent = total
            ? `${processed} / ${total} posts — ${this._formatEta(
                  etaSeconds
              )} remaining`
            : "";
    }

    _formatEta(seconds) {
        seconds = Math.max(0, Math.round(seconds || 0));
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
    }

    _evtFormSubmit(e) {
        e.preventDefault();
        this.dispatchEvent(new CustomEvent("submit", { detail: {} }));
    }

    _evtTagAllClick(e) {
        e.preventDefault();
        this.dispatchEvent(
            new CustomEvent("tagAll", { detail: { tagText: this.value } })
        );
    }

    _evtUntagAllClick(e) {
        e.preventDefault();
        this.dispatchEvent(
            new CustomEvent("untagAll", { detail: { tagText: this.value } })
        );
    }

    _evtOpenLinkClick(e) {
        e.preventDefault();
        this.toggleOpen(true);
        this.focus();
        this.dispatchEvent(new CustomEvent("open", { detail: {} }));
    }

    _evtCloseLinkClick(e) {
        e.preventDefault();
        if (this._running) {
            this.dispatchEvent(new CustomEvent("cancel", { detail: {} }));
            return;
        }
        this._inputNode.value = "";
        this.toggleOpen(false);
        this.blur();
        this.dispatchEvent(new CustomEvent("close", { detail: {} }));
    }
}

class BulkDeleteEditor extends BulkEditor {
    constructor(hostNode) {
        super(hostNode);
        this._hostNode.addEventListener("submit", (e) =>
            this._evtFormSubmit(e)
        );
    }

    _evtFormSubmit(e) {
        e.preventDefault();
        this.dispatchEvent(
            new CustomEvent("deleteSelectedPosts", { detail: {} })
        );
    }

    _evtOpenLinkClick(e) {
        e.preventDefault();
        this.toggleOpen(true);
        this.dispatchEvent(new CustomEvent("open", { detail: {} }));
    }

    _evtCloseLinkClick(e) {
        e.preventDefault();
        this.toggleOpen(false);
        this.dispatchEvent(new CustomEvent("close", { detail: {} }));
    }
}

class PostsHeaderView extends events.EventTarget {
    constructor(ctx) {
        super();

        ctx.settings = settings.get();
        this._ctx = ctx;
        this._hostNode = ctx.hostNode;
        views.replaceContent(this._hostNode, template(ctx));

        this._autoCompleteControl = new TagAutoCompleteControl(
            this._queryInputNode,
            {
                confirm: (tag) =>
                    this._autoCompleteControl.replaceSelectedText(
                        misc.escapeSearchTerm(tag.matchingNames[0]),
                        true
                    ),
                isNegationAllowed: true,
            }
        );

        keyboard.bind("p", () => this._focusFirstPostNode());
        search.searchInputNodeFocusHelper(this._queryInputNode);

        for (let safetyButtonNode of this._safetyButtonNodes) {
            safetyButtonNode.addEventListener("click", (e) =>
                this._evtSafetyButtonClick(e)
            );
        }
        this._formNode.addEventListener("submit", (e) =>
            this._evtFormSubmit(e)
        );

        this._bulkEditors = [];
        if (this._bulkEditTagsNode) {
            this._bulkTagEditor = new BulkTagEditor(this._bulkEditTagsNode);
            this._bulkEditors.push(this._bulkTagEditor);
        }

        if (this._bulkEditSafetyNode) {
            this._bulkSafetyEditor = new BulkSafetyEditor(
                this._bulkEditSafetyNode
            );
            this._bulkEditors.push(this._bulkSafetyEditor);
        }

        if (this._bulkEditDeleteNode) {
            this._bulkDeleteEditor = new BulkDeleteEditor(
                this._bulkEditDeleteNode
            );
            this._bulkEditors.push(this._bulkDeleteEditor);
        }

        for (let editor of this._bulkEditors) {
            editor.addEventListener("submit", (e) => {
                this._navigate();
            });
            editor.addEventListener("open", (e) => {
                this._hideBulkEditorsExcept(editor);
                this._navigate();
            });
            editor.addEventListener("close", (e) => {
                this._closeAndShowAllBulkEditors();
                this._navigate();
            });
        }

        if (this._bulkTagEditor) {
            this._bulkTagEditor.addEventListener("tagAll", (e) => {
                this.dispatchEvent(
                    new CustomEvent("tagAll", { detail: e.detail })
                );
            });
            this._bulkTagEditor.addEventListener("untagAll", (e) => {
                this.dispatchEvent(
                    new CustomEvent("untagAll", { detail: e.detail })
                );
            });
            this._bulkTagEditor.addEventListener("cancel", (e) => {
                this.dispatchEvent(
                    new CustomEvent("cancelTagAll", { detail: {} })
                );
            });
        }

        if (ctx.parameters.tag && this._bulkTagEditor) {
            this._openBulkEditor(this._bulkTagEditor);
        } else if (ctx.parameters.safety && this._bulkSafetyEditor) {
            this._openBulkEditor(this._bulkSafetyEditor);
        } else if (ctx.parameters.delete && this._bulkDeleteEditor) {
            this._openBulkEditor(this._bulkDeleteEditor);
        }
    }

    get _formNode() {
        return this._hostNode.querySelector("form.search");
    }

    get _safetyButtonNodes() {
        return this._hostNode.querySelectorAll("form .safety");
    }

    get _queryInputNode() {
        return this._hostNode.querySelector("form [name=search-text]");
    }

    get _bulkEditTagsNode() {
        return this._hostNode.querySelector(".bulk-edit-tags");
    }

    get _bulkEditSafetyNode() {
        return this._hostNode.querySelector(".bulk-edit-safety");
    }

    get _bulkEditDeleteNode() {
        return this._hostNode.querySelector(".bulk-edit-delete");
    }

    _openBulkEditor(editor) {
        editor.toggleOpen(true);
        this._hideBulkEditorsExcept(editor);
    }

    _hideBulkEditorsExcept(editor) {
        for (let otherEditor of this._bulkEditors) {
            if (otherEditor !== editor) {
                otherEditor.toggleOpen(false);
                otherEditor.toggleHide(true);
            }
        }
    }

    _closeAndShowAllBulkEditors() {
        for (let otherEditor of this._bulkEditors) {
            otherEditor.toggleOpen(false);
            otherEditor.toggleHide(false);
        }
    }

    _evtSafetyButtonClick(e, url) {
        e.preventDefault();
        e.target.classList.toggle("disabled");
        const safety = e.target.getAttribute("data-safety");
        let browsingSettings = settings.get();
        browsingSettings.listPosts[safety] =
            !browsingSettings.listPosts[safety];
        settings.save(browsingSettings, true);
        this.dispatchEvent(
            new CustomEvent("navigate", {
                detail: {
                    parameters: Object.assign({}, this._ctx.parameters, {
                        tag: null,
                        offset: 0,
                    }),
                },
            })
        );
    }

    _evtFormSubmit(e) {
        e.preventDefault();
        this._navigate();
    }

    _navigate() {
        this._autoCompleteControl.hide();
        let parameters = { query: this._queryInputNode.value };

        // convert falsy values to an empty string "" so that we can correctly compare with the current query
        const prevQuery = this._ctx.parameters.query
            ? this._ctx.parameters.query
            : "";
        parameters.offset =
            parameters.query === prevQuery ? this._ctx.parameters.offset : 0;
        if (this._bulkTagEditor && this._bulkTagEditor.opened) {
            parameters.tag = this._bulkTagEditor.value;
            this._bulkTagEditor.blur();
        } else {
            parameters.tag = null;
        }
        parameters.safety =
            this._bulkSafetyEditor && this._bulkSafetyEditor.opened
                ? "1"
                : null;
        parameters.delete =
            this._bulkDeleteEditor && this._bulkDeleteEditor.opened
                ? "1"
                : null;
        this.dispatchEvent(
            new CustomEvent("navigate", { detail: { parameters: parameters } })
        );
    }

    _focusFirstPostNode() {
        const firstPostNode = document.body.querySelector(
            ".post-list li:first-child a"
        );
        if (firstPostNode) {
            firstPostNode.focus();
        }
    }
}

module.exports = PostsHeaderView;
