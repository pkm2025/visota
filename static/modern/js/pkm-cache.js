/* pkm-cache.js — Client-side caching for PKM module using Dexie.js (IndexedDB).
 *
 * Database: pkm_cache
 * Stores:
 *   - drafts:         id (auto), title, content, updated_at
 *   - qa_history:     id (auto), question, answer, created_at
 *   - cached_results: query_hash (key), results, created_at
 *
 * Exposes a global PKMCache object with CRUD functions for drafts,
 * Q&A history, and cached search results.
 */
(function () {
    "use strict";

    // --- Database initialization -------------------------------------------------

    var db = new Dexie("pkm_cache");

    db.version(1).stores({
        drafts: "++id,title,content,updated_at",
        qa_history: "++id,question,answer,created_at",
        cached_results: "query_hash,results,created_at",
    });

    // Open the database (lazy, Dexie handles this internally on first query,
    // but calling open() eagerly surfaces any schema errors early).
    db.open().catch(function (err) {
        console.error("[PKM Cache] Failed to open IndexedDB:", err);
    });

    // --- Draft functions ---------------------------------------------------------

    /**
     * Save (or update) a draft note.
     * If a draft with the same title exists it is updated; otherwise a new
     * draft is created.
     * @param {string} title   - Draft title.
     * @param {string} content - Draft body content.
     * @returns {Promise<number>} Resolves with the draft id.
     */
    function saveDraft(title, content) {
        var now = new Date().toISOString();
        return db.drafts
            .where("title")
            .equals(title)
            .first()
            .then(function (existing) {
                if (existing) {
                    return db.drafts.update(existing.id, {
                        title: title,
                        content: content,
                        updated_at: now,
                    }).then(function () {
                        return existing.id;
                    });
                }
                return db.drafts.add({
                    title: title,
                    content: content,
                    updated_at: now,
                });
            });
    }

    /**
     * Get all drafts ordered by most-recently-updated first.
     * @returns {Promise<Array>} Resolves with array of draft objects.
     */
    function getDrafts() {
        return db.drafts.orderBy("updated_at").reverse().toArray();
    }

    /**
     * Delete a draft by its id.
     * @param {number} id - Draft id.
     * @returns {Promise<void>}
     */
    function deleteDraft(id) {
        return db.drafts.delete(id);
    }

    /**
     * Retrieve a single draft by title.
     * @param {string} title - Exact title to match.
     * @returns {Promise<Object|undefined>}
     */
    function getDraftByTitle(title) {
        return db.drafts.where("title").equals(title).first();
    }

    // --- Q&A history functions ---------------------------------------------------

    /**
     * Save a Q&A interaction to local cache.
     * @param {string} question - The user's question.
     * @param {string} answer   - The AI's answer.
     * @returns {Promise<number>} Resolves with the new record id.
     */
    function saveQAHistory(question, answer) {
        return db.qa_history.add({
            question: question,
            answer: answer,
            created_at: new Date().toISOString(),
        });
    }

    /**
     * Get recent Q&A history entries.
     * @param {number} [limit=20] - Maximum number of entries.
     * @returns {Promise<Array>} Resolves with array of Q&A objects (newest first).
     */
    function getQAHistory(limit) {
        if (limit === undefined || limit === null) {
            limit = 20;
        }
        return db.qa_history
            .orderBy("created_at")
            .reverse()
            .limit(limit)
            .toArray();
    }

    // --- Cached search results ---------------------------------------------------

    /**
     * Cache search results keyed by a query hash.
     * If an entry with the same query_hash exists it is updated.
     * @param {string} queryHash - Hash identifying the query.
     * @param {*}      results   - Search results (array or object).
     * @returns {Promise<void>}
     */
    function cacheResults(queryHash, results) {
        var now = new Date().toISOString();
        return db.cached_results
            .where("query_hash")
            .equals(queryHash)
            .first()
            .then(function (existing) {
                if (existing) {
                    return db.cached_results.update(existing.query_hash, {
                        results: results,
                        created_at: now,
                    });
                }
                return db.cached_results.add({
                    query_hash: queryHash,
                    results: results,
                    created_at: now,
                });
            });
    }

    /**
     * Retrieve cached search results by query hash.
     * @param {string} queryHash - Hash identifying the query.
     * @returns {Promise<Object|undefined>}
     */
    function getCachedResults(queryHash) {
        return db.cached_results
            .where("query_hash")
            .equals(queryHash)
            .first()
            .then(function (entry) {
                return entry ? entry.results : undefined;
            });
    }

    // --- Utility -----------------------------------------------------------------

    /**
     * Clear all PKM cache data (drafts, Q&A history, cached results).
     * @returns {Promise<void>}
     */
    function clearAll() {
        return Promise.all([
            db.drafts.clear(),
            db.qa_history.clear(),
            db.cached_results.clear(),
        ]);
    }

    // --- Background Sync: offline draft queueing ---------------------------

    var SYNC_TAG = "pkm-draft-sync";
    var QUEUE_DB = "pkm_sync_queue";
    var QUEUE_STORE = "outbox";

    /**
     * Open (or create) the IndexedDB outbox used by the client-side sync
     * helper. This mirrors the SW's outbox so the page can queue requests
     * even when the Background Sync API is unavailable (non-supporting
     * browsers). The SW also reads from this same database on 'sync'.
     * @returns {Promise<IDBDatabase>}
     */
    function openOutbox() {
        return new Promise(function (resolve, reject) {
            var req = indexedDB.open(QUEUE_DB, 1);
            req.onupgradeneeded = function () {
                var database = req.result;
                if (!database.objectStoreNames.contains(QUEUE_STORE)) {
                    database.createObjectStore(QUEUE_STORE, {
                        keyPath: "id",
                        autoIncrement: true,
                    });
                }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }

    /**
     * Queue a draft note POST for background sync.
     * Stores the serialized request in the outbox and registers a sync
     * event if the Background Sync API is available.
     * @param {string} url     - Target API URL (e.g. /api/v1/pkm/notes/).
     * @param {string} method  - HTTP method (POST or PUT).
     * @param {object} body    - JSON-serializable request body.
     * @param {object} [headers] - Extra headers (e.g. X-CSRFToken).
     * @returns {Promise<number>} Resolves with the outbox entry id.
     */
    function queueForSync(url, method, body, headers) {
        var entry = {
            url: url,
            method: method,
            headers: headers || {},
            body: JSON.stringify(body),
            timestamp: Date.now(),
        };
        return openOutbox().then(function (database) {
            return new Promise(function (resolve, reject) {
                var tx = database.transaction(QUEUE_STORE, "readwrite");
                var addReq = tx.objectStore(QUEUE_STORE).add(entry);
                addReq.onsuccess = function () {
                    resolve(addReq.result);
                };
                tx.onerror = function () { reject(tx.error); };
            }).then(function (id) {
                database.close();
                // Register for background sync if supported
                if ("serviceWorker" in navigator && "SyncManager" in window) {
                    navigator.serviceWorker.ready.then(function (reg) {
                        return reg.sync.register(SYNC_TAG);
                    }).catch(function () {
                        /* SW not ready yet; queue will sync on next 'sync' or manual trigger */
                    });
                }
                return id;
            });
        });
    }

    /**
     * Get the count of queued (unsynced) requests in the outbox.
     * @returns {Promise<number>}
     */
    function getQueuedCount() {
        return openOutbox().then(function (database) {
            return new Promise(function (resolve, reject) {
                var tx = database.transaction(QUEUE_STORE, "readonly");
                var countReq = tx.objectStore(QUEUE_STORE).count();
                countReq.onsuccess = function () { resolve(countReq.result); };
                countReq.onerror = function () { reject(countReq.error); };
            }).then(function (count) {
                database.close();
                return count;
            });
        }).catch(function () { return 0; });
    }

    /**
     * Get all queued requests from the outbox (for debugging / UI display).
     * @returns {Promise<Array>}
     */
    function getQueuedRequests() {
        return openOutbox().then(function (database) {
            return new Promise(function (resolve, reject) {
                var tx = database.transaction(QUEUE_STORE, "readonly");
                var allReq = tx.objectStore(QUEUE_STORE).getAll();
                allReq.onsuccess = function () { resolve(allReq.result); };
                allReq.onerror = function () { reject(allReq.error); };
            }).then(function (items) {
                database.close();
                return items;
            });
        }).catch(function () { return []; });
    }

    /**
     * Trigger a manual sync replay. Useful when the Background Sync API
     * is not available or as a fallback when coming back online.
     * Posts a message to the SW to replay the queue.
     * @returns {Promise<void>}
     */
    function triggerSync() {
        if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage("PKM_SYNC_NOW");
        }
        return Promise.resolve();
    }

    /**
     * Register a listener for sync status messages from the service worker.
     * The callback receives { type, url, status?, error? }.
     * @param {function} callback - Called when a sync event message arrives.
     * @returns {function} Unregister function.
     */
    function onSyncMessage(callback) {
        if (!("serviceWorker" in navigator)) {
            return function () {};
        }
        var handler = function (event) {
            if (event.data && typeof event.data.type === "string" &&
                event.data.type.indexOf("pkm:sync") === 0) {
                callback(event.data);
            }
        };
        navigator.serviceWorker.addEventListener("message", handler);
        return function () {
            navigator.serviceWorker.removeEventListener("message", handler);
        };
    }

    // --- Expose global -----------------------------------------------------------

    var PKMCache = {
        db: db,
        saveDraft: saveDraft,
        getDrafts: getDrafts,
        deleteDraft: deleteDraft,
        getDraftByTitle: getDraftByTitle,
        saveQAHistory: saveQAHistory,
        getQAHistory: getQAHistory,
        cacheResults: cacheResults,
        getCachedResults: getCachedResults,
        clearAll: clearAll,
        queueForSync: queueForSync,
        getQueuedCount: getQueuedCount,
        getQueuedRequests: getQueuedRequests,
        triggerSync: triggerSync,
        onSyncMessage: onSyncMessage,
    };

    // Expose on window for non-module usage (browser globals).
    if (typeof window !== "undefined") {
        window.PKMCache = PKMCache;
    }
})();
