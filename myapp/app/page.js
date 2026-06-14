'use client';

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const quickPrompts = [
  "Find a minimalist desk lamp under $80",
  "Compare wireless earbuds for workouts",
  "Show eco-friendly water bottles",
];

const starterMessages = [
  {
    id: 1,
    role: "assistant",
    text: "Hi there! I'm your AI shopping assistant. Tell me what you're looking for, or upload an image to start a visual search.",
  },
];

const focusModes = [
  { key: "budget", label: "Budget match" },
  { key: "speed", label: "Fast delivery" },
  { key: "eco", label: "Eco materials" },
];

export default function Page() {
  const [messages, setMessages] = useState(starterMessages);
  const [input, setInput] = useState("");
  const [image, setImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [modes, setModes] = useState({
    budget: true,
    speed: true,
    eco: false,
  });

  const sessionIdRef = useRef(
    `session-${Math.random().toString(36).slice(2, 10)}`
  );

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const messagesEndRef = useRef(null);

  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, image]);

  useEffect(() => {
    return () => {
      if (image?.url) {
        URL.revokeObjectURL(image.url);
      }
    };
  }, [image?.url]);

  const buildModeHint = () => {
    const hints = [];
    if (modes.budget) hints.push("budget-friendly");
    if (modes.speed) hints.push("fast delivery");
    if (modes.eco) hints.push("eco materials");
    if (hints.length === 0) return "";
    return ` Focus on ${hints.join(", ")}.`;
  };

  const handleSend = async (value = input) => {
    const trimmed = value.trim();
    if (!trimmed && !image) return;

    const stamp = Date.now();
    const userMessage = {
      id: stamp,
      role: "user",
      text: trimmed,
      image: image?.url || null,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInput("");

    try {
      let response;
      if (image) {
        const formData = new FormData();
        formData.append("file", image.file);
        formData.append("session_id", sessionIdRef.current);

        formData.append(
          "message", `${trimmed}${buildModeHint()}`
        )

        response = await fetch(`${apiBase}/image-search`, {
          method: "POST",
          body: formData,
        });
      } else {
        const messageWithModes = `${trimmed}${buildModeHint()}`;
        response = await fetch(`${apiBase}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            message: messageWithModes,
          }),
        });
      }

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage = {
        id: stamp + 1,
        role: "assistant",
        text: data.message || "Here are the best matches I found.",
        products: data.products || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const assistantMessage = {
        id: stamp + 1,
        role: "assistant",
        text: "Sorry, I couldn't reach the server. Please try again.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
      setImage(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = null;
      }
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (image?.url) {
      URL.revokeObjectURL(image.url);
    }
    setImage({ file, url: URL.createObjectURL(file), name: file.name });
    event.target.value = null; // Reset file input
  };

  const handleClearChat = () => {
    setMessages(starterMessages);
    setInput("");
    setImage(null);
    setIsLoading(false);
  };

  const toggleMode = (key) => {
    setModes((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="flex h-screen w-full bg-[#171717] text-slate-100 font-sans overflow-hidden">

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[260px] flex-col bg-[#0d0d0d] border-r border-[#2a2a2a] p-3 shrink-0">
        <button
          onClick={handleClearChat}
          className="flex w-full items-center gap-2 rounded-lg bg-[#171717] px-3 py-2 text-sm text-slate-200 transition hover:bg-[#212121] border border-[#2a2a2a]"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
          New search
        </button>

        <div className="mt-8 flex flex-col gap-2 px-1">
          <span className="text-xs font-semibold text-[#888]">Image Search</span>
          <label className="mt-2 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-[#333] bg-[#171717] p-4 text-center transition hover:border-[#555]">
            {image ? (
              <img src={image.url} alt="Uploaded" className="h-20 w-full rounded-md object-cover" />
            ) : (
              <>
                <svg className="h-5 w-5 text-[#888]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                <span className="text-xs text-[#888]">Upload image</span>
              </>
            )}
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
          </label>
          {image && (
            <button onClick={() => setImage(null)} className="mt-1 text-xs text-red-400 hover:text-red-300 text-left">Remove image</button>
          )}
        </div>

        <div className="mt-8 flex flex-col gap-2 px-1">
          <span className="text-xs font-semibold text-[#888]">Focus Modes</span>
          <div className="mt-2 flex flex-col gap-1">
            {focusModes.map((mode) => (
              <button
                key={mode.key}
                onClick={() => toggleMode(mode.key)}
                className={`flex items-center justify-between rounded-lg px-2 py-2 text-sm transition ${modes[mode.key] ? "bg-[#212121] text-slate-200" : "text-[#888] hover:bg-[#1a1a1a]"
                  }`}
              >
                <span>{mode.label}</span>
                <div className={`h-3 w-6 rounded-full transition-colors ${modes[mode.key] ? "bg-white" : "bg-[#444]"}`}>
                  <div className={`mt-[2px] ml-[2px] h-2 w-2 rounded-full bg-black transition-transform ${modes[mode.key] ? "translate-x-3" : ""}`} />
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col h-full bg-[#212121] w-full min-w-0 relative">
        <header className="flex h-14 items-center justify-between border-b border-[#2a2a2a] bg-[#171717] px-4 md:hidden shrink-0">
          <span className="font-medium text-slate-200">Shopping Assistant</span>
          <button onClick={handleClearChat} className="text-sm text-[#888]">New chat</button>
        </header>

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 chat-scrollbar">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
            {messages.map((message) => {
              const isUser = message.role === "user";
              return (
                <div key={message.id} className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="mr-4 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#171717] border border-[#333]">
                      <span className="text-white text-xs">AI</span>
                    </div>
                  )}
                  {/* <div className={`max-w-[85%] md:max-w-[75%] ${isUser ? "bg-[#333] rounded-3xl px-5 py-3 text-slate-100" : "pt-1.5 text-slate-200"}`}>
                    {message.text && <p className="leading-relaxed text-[15px] whitespace-pre-wrap">{message.text}</p>}
                  </div> */}
                  <div
                    className={`max-w-[85%] md:max-w-[75%] ${isUser
                      ? "bg-[#333] rounded-3xl px-5 py-3 text-slate-100"
                      : "pt-1.5 text-slate-200"
                      }`}
                  >
                    {message.text && (
                      <ReactMarkdown
                        components={{
                          h1: ({ children }) => (
                            <h1 className="text-3xl md:text-4xl font-bold mt-8 mb-5 text-white border-b border-[#444] pb-2">
                              {children}
                            </h1>
                          ),

                          h2: ({ children }) => (
                            <h2 className="text-2xl font-bold mt-6 mb-3 text-blue-300">
                              {children}
                            </h2>
                          ),

                          h3: ({ children }) => (
                            <h3 className="text-xl font-semibold mt-5 mb-2 text-green-300">
                              {children}
                            </h3>
                          ),

                          p: ({ children }) => (
                            <p className="mb-3 leading-7 text-[15px]">
                              {children}
                            </p>
                          ),

                          ul: ({ children }) => (
                            <ul className="list-disc ml-5 mb-3">
                              {children}
                            </ul>
                          ),

                          ol: ({ children }) => (
                            <ol className="list-decimal ml-5 mb-3">
                              {children}
                            </ol>
                          ),

                          li: ({ children }) => (
                            <li className="mb-1">
                              {children}
                            </li>
                          ),

                          hr: () => (
                            <div className="my-6 border-t border-[#555]" />
                          ),

                          strong: ({ children }) => (
                            <strong className="font-bold text-white">
                              {children}
                            </strong>
                          ),

                          em: ({ children }) => (
                            <em className="italic text-slate-300">
                              {children}
                            </em>
                          ),

                          blockquote: ({ children }) => (
                            <blockquote className="border-l-4 border-[#666] pl-4 my-3 text-slate-300">
                              {children}
                            </blockquote>
                          ),
                        }}
                      >
                        {message.text}
                      </ReactMarkdown>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        {/* Input Box Area */}
        <div className="w-full bg-[#212121] pb-6 pt-2 px-4 md:px-8 shrink-0">
          <div className="mx-auto w-full max-w-3xl relative">

            {messages.length === 1 && (
              <div className="mb-4 flex flex-wrap justify-center gap-2">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSend(prompt)}
                    className="rounded-xl border border-[#333] bg-[#1a1a1a] px-4 py-2 text-xs text-slate-300 transition hover:bg-[#2a2a2a] hover:text-white"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            <div className="relative flex flex-col rounded-3xl border border-[#444] bg-[#2f2f2f] focus-within:border-[#666] transition-colors shadow-sm">

              {/* Floating attached image */}
              {image && (
                <div className="absolute -top-14 left-2 flex items-center gap-2 rounded-lg border border-[#444] bg-[#2a2a2a] p-1.5 shadow-md">
                  <img src={image.url} alt="To send" className="h-9 w-9 rounded object-cover" />
                  <div className="flex flex-col max-w-[120px]">
                    <span className="text-xs text-slate-200 truncate">{image.name || 'Image'}</span>
                    <span className="text-[10px] text-[#888]">Attached</span>
                  </div>
                  <button onClick={() => setImage(null)} className="ml-1 mr-1 text-[#888] hover:text-white">
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                  </button>
                </div>
              )}

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={1}
                placeholder="Message Shopping Agent..."
                className="max-h-48 min-h-[56px] w-full resize-none rounded-3xl bg-transparent px-4 py-[16px] pr-14 text-[15px] text-slate-100 placeholder:text-[#888] focus:outline-none chat-scrollbar"
              />

              <div className="absolute bottom-[8px] right-2 flex gap-1">
                {/* Mobile image attach button */}
                <label className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-full text-[#888] transition hover:bg-[#3a3a3a] hover:text-white md:hidden">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                  <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                </label>

                <button
                  onClick={() => handleSend()}
                  disabled={(!input.trim() && !image) || isLoading}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-black transition hover:bg-slate-200 disabled:opacity-30 disabled:hover:bg-white"
                >
                  {isLoading ? (
                    <span className="text-xs">...</span>
                  ) : (
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7"></path></svg>
                  )}
                </button>
              </div>

            </div>

            <p className="mt-3 text-center text-xs text-[#666]">
              Shopping Agent may produce inaccurate information. Please double check details.
            </p>
          </div>
        </div>
      </main>

    </div>
  );
}
