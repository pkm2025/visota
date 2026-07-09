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
    };

    // Expose on window for non-module usage (browser globals).
    if (typeof window !== "undefined") {
        window.PKMCache = PKMCache;
    }
})();
