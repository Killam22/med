import Login from "./components/Login";
import Register from "./components/Register";
import Auth from "./components/Auth";

function App() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-[#D1DFEC] font-sans">
      <div className="bg-white w-[1200px] h-[650px] shadow-2xl  relative rounded-xl border border-[#D1DFEC] overflow-hidden">
        <Login />
        <Register />
        <Auth />
      </div>
    </div>
  );
}

export default App;
