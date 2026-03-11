import { useState } from "react";
import { User, EyeOff, Facebook, Eye } from "lucide-react";

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  return (
    <section className="relative h-full flex items-center justify-center bg-[#D1DFEC]">
      <div className="grid grid-cols-1 lg:grid-cols-2 w-full h-full bg-white overflow-hidden">
        {/* Left Side: Login Form Area */}
        <div className="flex flex-col justify-center px-16 py-16">
          <div className="max-w-md w-full mx-auto text-center">
            <h2 className="text-5xl font-semibold text-black mb-16">Login</h2>

            <div className="space-y-10">
              {/* Email Input */}
              <div className="relative group">
                <span className="absolute -top-3 left-6 px-2 bg-white text-base font-medium text-[#365885] z-10">
                  Email
                </span>
                <div className="relative">
                  <input
                    type="email"
                    className="w-full pl-6 pr-14 py-5 rounded-[20px] border-[1.5px] border-[#365885]/60 hover:border-[#365885] focus:border-[#365885] focus:ring-0 transition-all outline-none text-gray-700 text-lg"
                    placeholder="Email"
                  />
                  <div className="absolute right-5 top-1/2 -translate-y-1/2 text-[#365885]">
                    <User size={28} />
                  </div>
                </div>
              </div>

              {/* Password Input */}
              <div className="relative group">
                <label className="absolute -top-3 left-6 px-1.5 bg-white text-base font-medium text-[#365885] z-10">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    className="w-full pl-6 pr-14 py-5 rounded-[20px] border-[1.5px] border-[#365885]/60 hover:border-[#365885] focus:border-[#365885] focus:ring-0 transition-all outline-none text-gray-700 text-lg"
                    placeholder="•••••••••••"
                  />
                  <div
                    className="absolute right-5 top-1/2 -translate-y-1/2 text-[#365885] cursor-pointer"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <Eye size={28} /> : <EyeOff size={28} />}
                  </div>
                </div>
              </div>

              <div className="flex justify-center">
                <a
                  href="#"
                  className="-mt-7 text-sm font-medium text-gray-500 hover:text-[#365885] hover:underline transition-colors"
                >
                  Forgot password?
                </a>
              </div>

              <div className="space-y-6">
                <button className="w-full py-4 bg-[#6492C9] hover:bg-[#537db1] text-white text-xl font-semibold rounded-[20px] transition-all duration-200 shadow-sm cursor-pointer">
                  Login
                </button>

                <div className="flex flex-col items-center gap-4">
                  <p className="text-sm font-medium text-gray-500">
                    or login with social platforms
                  </p>

                  <div className="flex gap-4">
                    <button className="w-16 h-16 flex items-center justify-center bg-white border border-gray-200 rounded-[20px] hover:bg-gray-100 transition-all cursor-pointer shadow-sm">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 48 48"
                        width="30"
                        height="30"
                      >
                        <path
                          fill="#0a0a0aff"
                          d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
                        />
                      </svg>
                    </button>
                    <button className="w-16 h-16 flex items-center justify-center bg-white border border-gray-200 rounded-[20px] hover:bg-gray-100 transition-all cursor-pointer shadow-sm">
                      <Facebook size={28} fill="#000000ff" strokeWidth={0} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Decorative Area */}
        <div className="hidden lg:flex bg-gradient-to-br from-[#304B71] to-[#6492C9] items-center justify-center relative rounded-l-[250px] overflow-hidden">
          <div className="relative z-10 text-center flex flex-col items-center px-12">
            {/* Doctor Image */}
            <div className="-mb-6 max-w-[480px]">
              <img
                src="/Doctor_new.png"
                alt="Doctor Illustration"
                className="w-full h-auto object-contain"
              />
            </div>

            {/* Registration Prompt */}
            <div className="space-y-3">
              <p className="text-white text-base font-medium opacity-80">
                Don't have an account?
              </p>
              <button className="px-16 py-3 border-[1.5px] border-white/60 rounded-2xl text-white text-lg font-semibold hover:bg-white/10 transition-all cursor-pointer uppercase tracking-wide">
                REGISTER
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
