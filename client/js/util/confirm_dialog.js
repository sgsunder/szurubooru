"use strict";

// Lightweight custom confirmation modal, used where the plain-text
// window.confirm() isn't expressive enough.
//
// `blocks` is an array where each entry is either a plain string (rendered
// as a paragraph) or `{monospace: true, text: string}` (rendered as a
// preformatted block). Returns a Promise<boolean> resolving to whether the
// user confirmed.
function showConfirmDialog(blocks) {
    return new Promise((resolve) => {
        const overlayNode = document.createElement("div");
        overlayNode.className = "confirm-dialog-overlay";

        const dialogNode = document.createElement("div");
        dialogNode.className = "confirm-dialog";
        overlayNode.appendChild(dialogNode);

        for (let block of blocks) {
            const monospace = typeof block === "object" && block.monospace;
            const text = typeof block === "object" ? block.text : block;
            const blockNode = document.createElement(monospace ? "pre" : "p");
            blockNode.className = monospace
                ? "confirm-dialog-mono"
                : "confirm-dialog-text";
            blockNode.textContent = text;
            dialogNode.appendChild(blockNode);
        }

        const buttonsNode = document.createElement("div");
        buttonsNode.className = "confirm-dialog-buttons";
        dialogNode.appendChild(buttonsNode);

        const cancelButtonNode = document.createElement("button");
        cancelButtonNode.type = "button";
        cancelButtonNode.className = "confirm-dialog-cancel";
        cancelButtonNode.textContent = "Cancel";
        buttonsNode.appendChild(cancelButtonNode);

        const confirmButtonNode = document.createElement("button");
        confirmButtonNode.type = "button";
        confirmButtonNode.className = "confirm-dialog-confirm";
        confirmButtonNode.textContent = "Continue";
        buttonsNode.appendChild(confirmButtonNode);

        function close(result) {
            document.removeEventListener("keydown", evtKeyDown);
            overlayNode.remove();
            resolve(result);
        }

        function evtKeyDown(e) {
            if (e.key === "Escape") {
                close(false);
            }
        }

        confirmButtonNode.addEventListener("click", () => close(true));
        cancelButtonNode.addEventListener("click", () => close(false));
        overlayNode.addEventListener("click", (e) => {
            if (e.target === overlayNode) {
                close(false);
            }
        });
        document.addEventListener("keydown", evtKeyDown);

        document.body.appendChild(overlayNode);
        confirmButtonNode.focus();
    });
}

module.exports = {
    showConfirmDialog: showConfirmDialog,
};
