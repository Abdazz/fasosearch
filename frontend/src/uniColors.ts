import { useEffect, useState } from "react";
import { api } from "./api";
import { uniColorMap } from "./utils";

// Source canonique et unique des couleurs par université.
//
// Avant ce module, Lab.tsx et Corpus.tsx appelaient chacun `uniColorMap(...)`
// avec leur propre liste : Lab à partir de `/api/map` (une seule affiliation
// par point, la première), Corpus à partir de `/api/corpus` (toutes les
// affiliations séparées). Ces deux listes ne coïncident pas forcément (une
// université qui n'apparaît jamais en première affiliation manque de la liste
// de Lab), donc le tri interne de `uniColorMap` ne portait pas sur le même
// ensemble : la même université pouvait recevoir deux couleurs différentes
// selon la page visitée en premier (constaté : UNB orange sur la carte mais
// citron vert dans le corpus, UJKZ rouge vs vert).
//
// Ce module ne charge la couleur qu'une seule fois pour toute l'application,
// à partir d'une unique source de vérité : la liste complète et triée des
// universités renvoyée par `/api/corpus` (`universities[].name`, qui contient
// déjà chaque affiliation séparée par le backend). Peu importe quelle page
// (Lab, Corpus, ou un simple `<UniBadge>` isolé) déclenche le chargement en
// premier : le résultat est toujours calculé à partir de la même liste.
let loadPromise: Promise<void> | null = null;
const listeners = new Set<() => void>();

function ensureLoaded(): void {
  if (loadPromise) return;
  loadPromise = api.corpus()
    .then((d) => {
      uniColorMap(d.universities.map((u) => u.name));
      listeners.forEach((fn) => fn());
    })
    .catch(() => {
      // Échec réseau : on retente au prochain montage plutôt que de rester
      // bloqué indéfiniment sur le repli par hachage de `uniColor()`.
      loadPromise = null;
    });
}

/**
 * À appeler dans tout composant qui affiche une couleur d'université
 * (`uniColor(name)`). Déclenche le chargement canonique une seule fois pour
 * toute l'appli (idempotent, partagé), et force un nouveau rendu du composant
 * appelant lorsque la palette canonique devient disponible, pour que la
 * couleur de repli (hachage) affichée avant le chargement soit remplacée par
 * la couleur définitive sans qu'il soit nécessaire de recharger la page.
 */
export function useUniColor(): void {
  const [, setTick] = useState(0);
  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    listeners.add(listener);
    ensureLoaded();
    return () => { listeners.delete(listener); };
  }, []);
}
