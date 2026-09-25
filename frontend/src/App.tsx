import Backdrop from "./components/Backdrop";
import Nav from "./components/Nav";
import Author from "./pages/Author";
import Authors from "./pages/Authors";
import Compare from "./pages/Compare";
import Corpus from "./pages/Corpus";
import Home from "./pages/Home";
import Lab from "./pages/Lab";
import Results from "./pages/Results";
import { useRoute } from "./router";
import { useUniColor } from "./uniColors";

export default function App() {
  const { page, params } = useRoute();
  // Déclenche le chargement de la palette canonique de couleurs d'université
  // dès le démarrage de l'appli, quelle que soit la première page visitée.
  useUniColor();
  return (
    <>
      <Backdrop />
      <div className="wrap">
        <Nav page={page} />
        <main key={page}>
          {page === "home" && <Home />}
          {page === "search" && <Results params={params} />}
          {page === "compare" && <Compare params={params} />}
          {page === "lab" && <Lab params={params} />}
          {page === "corpus" && <Corpus params={params} />}
          {page === "authors" && <Authors params={params} />}
          {page === "author" && <Author params={params} />}
        </main>
      </div>
    </>
  );
}
