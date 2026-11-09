/*
 * Service worker de K+ Studio : rend l'application installable et utilisable
 * sans Internet.
 *
 * - À l'installation, il met en cache tous les fichiers de K+ Studio (liste
 *   écrite par construire.py) et les fichiers de Pyodide (Python).
 * - Ensuite, ces fichiers sont servis depuis le cache : K+ Studio démarre
 *   même hors ligne.
 * - Chaque nouvelle version publiée a un numéro différent (VERSION) : le
 *   navigateur la télécharge, et la page propose de recharger.
 */
"use strict";

const VERSION = "__VERSION__";                     // remplacé par construire.py
const FICHIERS_STUDIO = __FICHIERS__;               // remplacé par construire.py
const VERSION_PYODIDE = "0.27.7";
const URL_PYODIDE = `https://cdn.jsdelivr.net/npm/pyodide@${VERSION_PYODIDE}/`;
const FICHIERS_PYODIDE = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
                          "python_stdlib.zip", "pyodide-lock.json"];

const CACHE_STUDIO = `kplus-studio-${VERSION}`;
const CACHE_PYODIDE = `kplus-pyodide-${VERSION_PYODIDE}`;

self.addEventListener("install", (evenement) => {
  evenement.waitUntil((async () => {
    const studio = await caches.open(CACHE_STUDIO);
    // cache: "reload" évite de recopier une ancienne version du cache HTTP.
    await studio.addAll(FICHIERS_STUDIO.map((f) => new Request(f, { cache: "reload" })));
    const pyodide = await caches.open(CACHE_PYODIDE);
    for (const fichier of FICHIERS_PYODIDE) {
      const url = URL_PYODIDE + fichier;
      if (!(await pyodide.match(url))) await pyodide.add(url);
    }
  })());
});

self.addEventListener("activate", (evenement) => {
  evenement.waitUntil((async () => {
    for (const nom of await caches.keys()) {
      if (nom.startsWith("kplus-") && nom !== CACHE_STUDIO && nom !== CACHE_PYODIDE) {
        await caches.delete(nom);
      }
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", (evenement) => {
  if (evenement.data === "mettre-a-jour") self.skipWaiting();
});

self.addEventListener("fetch", (evenement) => {
  const requete = evenement.request;
  if (requete.method !== "GET") return;
  const url = new URL(requete.url);

  // Pyodide : adresses fixes (version précise), donc « cache d'abord ».
  if (requete.url.startsWith(URL_PYODIDE)) {
    evenement.respondWith((async () => {
      const cache = await caches.open(CACHE_PYODIDE);
      const enCache = await cache.match(requete.url);
      if (enCache) return enCache;
      const reponse = await fetch(requete);
      if (reponse.ok) cache.put(requete.url, reponse.clone());
      return reponse;
    })());
    return;
  }

  // Fichiers de K+ Studio : depuis le cache de cette version, sinon réseau.
  if (url.origin === self.location.origin) {
    evenement.respondWith((async () => {
      const cache = await caches.open(CACHE_STUDIO);
      const enCache = await cache.match(requete, { ignoreSearch: true });
      if (enCache) return enCache;
      try {
        return await fetch(requete);
      } catch (erreur) {
        // Hors ligne : une navigation vers l'application ouvre index.html.
        if (requete.mode === "navigate") {
          const accueil = await cache.match("index.html");
          if (accueil) return accueil;
        }
        throw erreur;
      }
    })());
  }
});
