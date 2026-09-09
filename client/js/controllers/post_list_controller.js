"use strict";

const router = require("../router.js");
const api = require("../api.js");
const misc = require("../util/misc.js");
const confirmDialog = require("../util/confirm_dialog.js");
const settings = require("../models/settings.js");
const uri = require("../util/uri.js");
const PostList = require("../models/post_list.js");
const topNavigation = require("../models/top_navigation.js");
const PageController = require("../controllers/page_controller.js");
const PostsHeaderView = require("../views/posts_header_view.js");
const PostsPageView = require("../views/posts_page_view.js");
const EmptyView = require("../views/empty_view.js");

const fields = [
    "id",
    "thumbnailUrl",
    "type",
    "safety",
    "score",
    "favoriteCount",
    "commentCount",
    "tags",
    "version",
];

// no server-side rate limiting or bulk-edit endpoint exists, so an unbounded
// Promise.all over a large search result would fire that many simultaneous
// requests; this keeps a small, fixed amount of parallelism instead.
const BULK_TAG_CONCURRENCY = 4;

class PostListController {
    constructor(ctx) {
        this._pageController = new PageController();

        if (!api.hasPrivilege("posts:list")) {
            this._view = new EmptyView();
            this._view.showError("You don't have privileges to view posts.");
            return;
        }

        this._ctx = ctx;

        topNavigation.activate("posts");
        topNavigation.setTitle("Listing posts");

        this._headerView = new PostsHeaderView({
            hostNode: this._pageController.view.pageHeaderHolderNode,
            parameters: ctx.parameters,
            enableSafety: api.safetyEnabled(),
            canBulkEditTags: api.hasPrivilege("posts:bulk-edit:tags"),
            canBulkEditSafety: api.hasPrivilege("posts:bulk-edit:safety"),
            canBulkDelete: api.hasPrivilege("posts:bulk-edit:delete"),
            bulkEdit: {
                tags: this._bulkEditTags,
            },
        });
        this._headerView.addEventListener("navigate", (e) =>
            this._evtNavigate(e),
        );

        if (this._headerView._bulkDeleteEditor) {
            this._headerView._bulkDeleteEditor.addEventListener(
                "deleteSelectedPosts",
                (e) => {
                    this._evtDeleteSelectedPosts(e);
                },
            );
        }

        if (this._headerView._bulkTagEditor) {
            this._headerView.addEventListener("tagAll", (e) =>
                this._evtTagAll(e),
            );
            this._headerView.addEventListener("untagAll", (e) =>
                this._evtUntagAll(e),
            );
            this._headerView.addEventListener("cancelTagAll", (e) =>
                this._evtCancelTagAll(e),
            );
        }

        this._postsMarkedForDeletion = [];
        this._bulkTagOperation = null;
        this._syncPageController();
    }

    showSuccess(message) {
        this._pageController.showSuccess(message);
    }

    showError(message) {
        this._pageController.showError(message);
    }

    get _bulkEditTags() {
        return (this._ctx.parameters.tag || "").split(/\s+/).filter((s) => s);
    }

    _evtNavigate(e) {
        router.showNoDispatch(
            uri.formatClientLink("posts", e.detail.parameters),
        );
        Object.assign(this._ctx.parameters, e.detail.parameters);
        this._syncPageController();
    }

    _evtTag(e) {
        Promise.all(
            this._bulkEditTags.map((tag) => e.detail.post.tags.addByName(tag)),
        )
            .then(e.detail.post.save())
            .catch((error) => window.alert(error.message));
    }

    _evtUntag(e) {
        for (let tag of this._bulkEditTags) {
            e.detail.post.tags.removeByName(tag);
        }
        e.detail.post.save().catch((error) => window.alert(error.message));
    }

    _evtChangeSafety(e) {
        e.detail.post.safety = e.detail.safety;
        e.detail.post.save().catch((error) => window.alert(error.message));
    }

    _evtMarkForDeletion(e) {
        const postId = e.detail;

        // Add or remove post from delete list
        if (e.detail.delete) {
            this._postsMarkedForDeletion.push(e.detail.post);
        } else {
            this._postsMarkedForDeletion = this._postsMarkedForDeletion.filter(
                (x) => x.id != e.detail.post.id,
            );
        }
    }

    _evtDeleteSelectedPosts(e) {
        if (this._postsMarkedForDeletion.length == 0) return;

        if (
            confirm(
                `Are you sure you want to delete ${this._postsMarkedForDeletion.length} posts?`,
            )
        ) {
            Promise.all(
                this._postsMarkedForDeletion.map((post) => post.delete()),
            )
                .catch((error) => window.alert(error.message))
                .then(() => {
                    this._postsMarkedForDeletion = [];
                    this._headerView._navigate();
                });
        }
    }

    _evtTagAll(e) {
        this._startBulkTagOperation(e.detail.tagText, "add");
    }

    _evtUntagAll(e) {
        this._startBulkTagOperation(e.detail.tagText, "remove");
    }

    _evtCancelTagAll(e) {
        if (this._bulkTagOperation) {
            this._bulkTagOperation.cancelled = true;
        }
    }

    _startBulkTagOperation(tagText, mode) {
        const tags = misc.splitByWhitespace(tagText || "");
        if (!tags.length) {
            window.alert("Please enter at least one tag.");
            return;
        }

        PostList.search(this._ctx.parameters.query, 0, 1, ["id"])
            .then((response) => {
                if (!response.total) {
                    window.alert("No posts match the current search query.");
                    return;
                }

                const verb = mode === "add" ? "add" : "remove";
                const prep = mode === "add" ? "to" : "from";
                const queryBlock = this._ctx.parameters.query
                    ? { monospace: true, text: this._ctx.parameters.query }
                    : "(empty query — this matches ALL posts on the site)";
                const blocks = [
                    `This will ${verb} the tag(s):`,
                    { monospace: true, text: tags.join("\n") },
                    `${prep} all ${response.total} post(s) matching the search query:`,
                    queryBlock,
                    "Continue?",
                ];

                return confirmDialog
                    .showConfirmDialog(blocks)
                    .then((confirmed) => {
                        if (!confirmed) {
                            return;
                        }
                        this._runBulkTagOperation(tags, mode, response.total);
                    });
            })
            .catch((error) => window.alert(error.message));
    }

    _runBulkTagOperation(tags, mode, total) {
        const cancellation = { cancelled: false };
        this._bulkTagOperation = cancellation;

        const editor = this._headerView._bulkTagEditor;
        editor.setRunning(true);
        editor.setProgress(0, total, 0);

        const startTime = Date.now();
        let processed = 0;
        let failed = 0;
        let offset = 0;
        const limit = 100; // server-enforced page size cap

        const applyToPost = (post) => {
            if (mode === "add") {
                return Promise.all(
                    tags.map((tag) => post.tags.addByName(tag)),
                ).then(() => post.save());
            }
            for (let tag of tags) {
                post.tags.removeByName(tag);
            }
            return post.save();
        };

        const runWorkerPool = (posts) => {
            let index = 0;
            const worker = () => {
                if (cancellation.cancelled || index >= posts.length) {
                    return Promise.resolve();
                }
                const post = posts.at(index++);
                return applyToPost(post)
                    .catch((error) => {
                        failed++;
                    })
                    .then(() => {
                        processed++;
                        const elapsedSeconds = (Date.now() - startTime) / 1000;
                        const rate =
                            processed / Math.max(elapsedSeconds, 0.001);
                        const etaSeconds =
                            rate > 0 ? (total - processed) / rate : 0;
                        editor.setProgress(processed, total, etaSeconds);
                        return worker();
                    });
            };
            const workers = [];
            for (let i = 0; i < BULK_TAG_CONCURRENCY; i++) {
                workers.push(worker());
            }
            return Promise.all(workers);
        };

        const fetchAndProcessNextPage = () => {
            if (cancellation.cancelled || offset >= total) {
                return Promise.resolve();
            }
            return PostList.search(
                this._ctx.parameters.query,
                offset,
                limit,
                fields,
            ).then((response) => {
                offset += limit;
                return runWorkerPool(response.results).then(() =>
                    fetchAndProcessNextPage(),
                );
            });
        };

        fetchAndProcessNextPage()
            .catch((error) => window.alert(error.message))
            .then(() => {
                this._finishBulkTagOperation(
                    cancellation.cancelled,
                    processed,
                    failed,
                );
            });
    }

    _finishBulkTagOperation(wasCancelled, processed, failed) {
        this._bulkTagOperation = null;
        this._headerView._bulkTagEditor.setRunning(false);
        this._headerView._navigate();

        const succeeded = processed - failed;
        if (wasCancelled) {
            this.showSuccess(
                `Cancelled: ${succeeded} post(s) updated, ${failed} failed before stopping.`,
            );
        } else if (failed > 0) {
            this.showError(
                `Finished with errors: ${succeeded} post(s) updated, ${failed} failed.`,
            );
        } else {
            this.showSuccess(`Done: ${succeeded} post(s) updated.`);
        }
    }

    _syncPageController() {
        this._pageController.run({
            parameters: this._ctx.parameters,
            defaultLimit: parseInt(settings.get().postsPerPage),
            getClientUrlForPage: (offset, limit) => {
                const parameters = Object.assign({}, this._ctx.parameters, {
                    offset: offset,
                    limit: limit,
                });
                return uri.formatClientLink("posts", parameters);
            },
            requestPage: (offset, limit) => {
                return PostList.search(
                    this._ctx.parameters.query,
                    offset,
                    limit,
                    fields,
                );
            },
            pageRenderer: (pageCtx) => {
                Object.assign(pageCtx, {
                    canViewPosts: api.hasPrivilege("posts:view"),
                    canBulkEditTags: api.hasPrivilege("posts:bulk-edit:tags"),
                    canBulkEditSafety: api.hasPrivilege(
                        "posts:bulk-edit:safety",
                    ),
                    canBulkDelete: api.hasPrivilege("posts:bulk-edit:delete"),
                    bulkEdit: {
                        tags: this._bulkEditTags,
                        markedForDeletion: this._postsMarkedForDeletion,
                    },
                    postFlow: settings.get().postFlow,
                });
                const view = new PostsPageView(pageCtx);
                view.addEventListener("tag", (e) => this._evtTag(e));
                view.addEventListener("untag", (e) => this._evtUntag(e));
                view.addEventListener("changeSafety", (e) =>
                    this._evtChangeSafety(e),
                );
                view.addEventListener("markForDeletion", (e) =>
                    this._evtMarkForDeletion(e),
                );
                return view;
            },
        });
    }
}

module.exports = (router) => {
    router.enter(["posts"], (ctx, next) => {
        ctx.controller = new PostListController(ctx);
    });
};
