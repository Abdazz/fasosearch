import Backdrop from "./components/Backdrop";
import Nav from "./components/Nav";
import Compare from "./pages/Compare";
import Corpus from "./pages/Corpus";
import Home from "./pages/Home";
import Lab from "./pages/Lab";
import Results from "./pages/Results";
import { useRoute } from "./router";

export default function App() {
  const { page, params } = useRoute();
  return (
    <>
      <Backdrop />
      <div className="wrap">
        <Nav page={page} />
        <main key={page}>
          {page === "home" && <Home />}
          {page === "search" && <Results params={params} />}
          {page === "compare" && <Compare params={params} />}
          {page === "lab" && <Lab />}
          {page === "corpus" && <Corpus />}
        </main>
      </div>
    </>
  );
}
