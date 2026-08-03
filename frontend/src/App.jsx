import React, { useState } from 'react';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const DEFAULT_EMAIL = import.meta.env.VITE_DEMO_EMAIL || 'demo@rcpi.local';
const DEFAULT_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'demo1234';

export default function App() {
  const [sitePhoto, setSitePhoto] = useState(null);
  const [siteFile, setSiteFile] = useState(null);
  const [photoBase64, setPhotoBase64] = useState('');
  const [userPrompt, setUserPrompt] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [renderMode, setRenderMode] = useState('3d');
  const [activeTab, setActiveTab] = useState('studio');
  const [projectId, setProjectId] = useState(null);
  const [authToken, setAuthToken] = useState(localStorage.getItem('rcpi_token') || '');
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: '🏛️ **Welcome to RCPI Global Enterprise Landscape Intelligence Suite (v5.0 - Expert Edition).**\n\nLoaded with complete CPWD & International landscape engineering knowledge, automated 2D layout planning, cinematic 3D realistic rendering, and itemized institutional BOQs.\n\n*Select a professional prompt below or specify your exact site dimensions, terrain contours, and turf requirements.*'
    }
  ]);

  const ensureAuthenticated = async () => {
    if (authToken) return authToken;

    try {
      const registerResponse = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: DEFAULT_EMAIL,
          full_name: 'Demo User',
          password: DEFAULT_PASSWORD,
          role: 'client',
        }),
      });

      if (!registerResponse.ok && registerResponse.status !== 400) {
        throw new Error('Registration failed');
      }
    } catch (error) {
      console.warn('Register step skipped or failed', error);
    }

    const loginResponse = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: DEFAULT_EMAIL,
        password: DEFAULT_PASSWORD,
      }),
    });

    const loginData = await loginResponse.json();
    if (!loginResponse.ok || !loginData.access_token) {
      throw new Error(loginData.detail || 'Authentication failed');
    }

    localStorage.setItem('rcpi_token', loginData.access_token);
    setAuthToken(loginData.access_token);
    return loginData.access_token;
  };

  const ensureProject = async (token) => {
    if (projectId) return projectId;

    const projectResponse = await fetch(`${API_BASE}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: 'Demo Project',
        area_sqft: 180,
        preferred_style: 'Modern Indian Garden',
        image_filename: siteFile?.name || null,
      }),
    });

    const projectData = await projectResponse.json();
    if (!projectResponse.ok) {
      throw new Error(projectData.detail || 'Project creation failed');
    }

    setProjectId(projectData.id);
    return projectData.id;
  };

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSiteFile(file);
    setSitePhoto(URL.createObjectURL(file));

    const reader = new FileReader();
    reader.onloadend = () => {
      setPhotoBase64(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleQuickPrompt = (promptText) => {
    setUserPrompt(promptText);
  };

  const handleAnalyzeSite = async (e) => {
    if (e) e.preventDefault();

    if (!siteFile) {
      alert('Please upload a site image before starting the analysis workflow.');
      return;
    }

    const token = await ensureAuthenticated();
    const currentProjectId = await ensureProject(token);
    const currentPrompt = userPrompt.trim() || 'Landscape site analysis request';

    const userMsg = {
      role: 'user',
      text: currentPrompt,
      image: sitePhoto,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setUserPrompt('');

    try {
      const formData = new FormData();
      if (siteFile) {
        formData.append('image', siteFile);
      }
      formData.append('area_sqft', '180');
      formData.append('preferred_style', 'Modern Indian Garden');
      formData.append('render_mode', renderMode);

      const response = await fetch(`${API_BASE}/api/projects/${currentProjectId}/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Analysis request failed');
      }

      const boqs = (data.boq || []).map((item) => `${item.item}: ${item.quantity} • ${item.total_cost_inr}`).join('\n');
      const assistantText = [
        `✅ Project analyzed successfully for project #${data.project_id}.`,
        `Suggested style: ${data.suggested_style}`,
        `Estimated timeline: ${data.estimated_days} days`,
        `Total BOQ estimate: ${data.total_cost_inr}`,
        `\nBOQ lines:\n${boqs}`,
        `\nModel notes:\n${data.model_notes}`,
      ].join('\n');

      const renderSrc = data.render_base64 ? `data:image/png;base64,${data.render_base64}` : '';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: assistantText,
          render3D: renderMode === '3d' ? renderSrc : '',
          render2D: renderMode === '2d' ? renderSrc : '',
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `⚠️ **System Diagnostic Alert:** Request failed (${error.message}). Please verify the backend server and the project authorization flow.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleChatSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!chatInput.trim()) return;

    const token = await ensureAuthenticated();
    const currentProjectId = await ensureProject(token);

    const question = chatInput.trim();
    setChatInput('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/projects/${currentProjectId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: question }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Chat request failed');
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `⚠️ Chat request failed: ${error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 font-sans flex flex-col justify-between selection:bg-emerald-500 selection:text-black">
      <header className="w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 flex flex-wrap justify-between items-center shadow-xl">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 p-0.5 shadow-lg shadow-emerald-900/40 flex items-center justify-center">
            <img
              src="https://images.unsplash.com/photo-1541888946425-d0fbb18f7247?w=120&auto=format&fit=crop&q=80"
              alt="RCPI Logo"
              className="h-full w-full object-cover rounded-[10px]"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-black tracking-wider text-white uppercase">RCPI Landscape AI</h1>
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-semibold">v5.0 Expert Edition</span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">RCPI INDIA PRIVATE LIMITED • CIN: U45202GJ2021PTC131249</p>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-2 sm:mt-0">
          <div className="hidden md:flex bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
            <button
              onClick={() => setActiveTab('studio')}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${activeTab === 'studio' ? 'bg-emerald-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'}`}
            >
              AI Studio & Drawings
            </button>
            <button
              onClick={() => setActiveTab('specs')}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${activeTab === 'specs' ? 'bg-emerald-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'}`}
            >
              CPWD & DSR Specs
            </button>
            <button
              onClick={() => setActiveTab('helpdesk')}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${activeTab === 'helpdesk' ? 'bg-emerald-500 text-slate-950 font-bold shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Help Desk
            </button>
          </div>

          <div className="flex items-center gap-2 bg-emerald-950/60 border border-emerald-800/60 px-3.5 py-1.5 rounded-xl shadow-inner">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-semibold text-emerald-300">2D/3D Engine Active</span>
          </div>
        </div>
      </header>

      <main className="flex-grow w-full max-w-7xl mx-auto p-4 md:p-6 flex flex-col gap-6">
        {activeTab === 'studio' && (
          <div className="relative rounded-3xl overflow-hidden border border-slate-800 shadow-2xl bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:16px_16px]"></div>
            <div className="z-10 max-w-2xl space-y-3">
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-500/20 font-bold">
                ✨ Automated 2D CAD Drawings, 3D Masterplans & Complete BOQ
              </div>
              <h2 className="text-2xl md:text-3xl font-black text-white tracking-tight">
                Institutional Landscape Engineering & Design.
              </h2>
              <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
                Generate professional 2D layout blueprints, realistic 3D architectural renders, CPWD soil conditioning ratios, turf matrices, and itemized financial BOQs instantly.
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                <button onClick={() => handleQuickPrompt('Design a 10000 sqft luxury resort landscape with 3D contour mounding, Zoysia grass, stone pathway, pop-up sprinklers, and complete itemized BOQ.')} className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition">
                  🌴 Luxury Resort (2D & 3D + BOQ)
                </button>
                <button onClick={() => handleQuickPrompt('Plan a corporate campus green zone with vertical gardens, canopy trees, jogging track, solar LED lighting, and institutional BOQ.')} className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition">
                  🏢 Corporate Campus Masterplan
                </button>
                <button onClick={() => handleQuickPrompt('Provide 3000 sqft residential villa lawn, topsoil dressing 60:20:20 ratio, Mexican carpet grass, pergola, drip irrigation, and cost BOQ.')} className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition">
                  🏡 Modern Villa Lawn & Irrigation
                </button>
              </div>
            </div>

            <div className="z-10 w-full md:w-80 h-48 rounded-2xl overflow-hidden border border-slate-700 shadow-2xl relative group">
              <img
                src="https://images.unsplash.com/photo-1558904541-efa8c4a75f1b?w=600&auto=format&fit=crop&q=80"
                alt="Landscape Architecture Sample"
                className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-3">
                <span className="text-[11px] font-semibold text-emerald-400 bg-black/60 px-2.5 py-1 rounded-lg backdrop-blur-md">
                  RCPI Expert Render
                </span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'specs' && (
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 space-y-4">
            <h3 className="text-lg font-bold text-emerald-400">CPWD, DSR & Soil Engineering Standards</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              RCPI INDIA PRIVATE LIMITED adheres strictly to Central Public Works Department (CPWD) landscaping specifications, Delhi Schedule of Rates (DSR), and scientific horticultural standards.
              <br /><br />
              <strong>Key Parameters Enforced by AI:</strong>
              <br />• <strong>Soil Mix Ratio:</strong> Standard 60% screened red soil, 20% organic vermicompost/FYM, and 20% coarse river sand for optimal root aeration.
              <br />• <strong>Topsoil Dressing:</strong> Minimum 150mm to 300mm depth depending on turf and shrub requirements.
              <br />• <strong>Irrigation Hydraulics:</strong> Automated pop-up sprinklers with precipitation rate matching and pressure-compensating drip lines.
            </p>
          </div>
        )}

        {activeTab === 'helpdesk' && (
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 space-y-4">
            <h3 className="text-lg font-bold text-emerald-400">RCPI Global Help Desk & Support</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <h4 className="text-xs font-bold text-white">📧 Official Email</h4>
                <p className="text-xs text-slate-400 mt-1">RCPIINDIA.VADODARA@GMAIL.COM</p>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <h4 className="text-xs font-bold text-white">📞 Helpline Numbers</h4>
                <p className="text-xs text-slate-400 mt-1">+91-9737199772<br />+91-9406603778</p>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <h4 className="text-xs font-bold text-white">🏢 Corporate Headquarters</h4>
                <p className="text-xs text-slate-400 mt-1">Vadodara, Gujarat, India<br />CIN: U45202GJ2021PTC131249</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'studio' && (
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-3xl flex flex-col h-[65vh] shadow-2xl overflow-hidden backdrop-blur-md">
            <div className="flex-grow overflow-y-auto p-4 md:p-6 space-y-6">
              {messages.map((m, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[95%] md:max-w-[90%] rounded-2xl p-4 md:p-6 text-xs md:text-sm leading-relaxed whitespace-pre-wrap shadow-lg ${
                      m.role === 'user'
                        ? 'bg-emerald-500 text-slate-950 font-semibold rounded-br-none'
                        : 'bg-slate-950 text-slate-200 border border-slate-800/80 rounded-bl-none space-y-4'
                    }`}
                  >
                    {m.image && (
                      <div className="mb-3">
                        <img
                          src={m.image}
                          alt="Uploaded Site Reference"
                          className="w-64 h-40 object-cover rounded-xl border border-slate-700 shadow-md"
                        />
                      </div>
                    )}

                    {m.render2D && (
                      <div className="bg-slate-900 p-3 rounded-2xl border border-emerald-500/30">
                        <p className="text-[11px] font-bold text-emerald-400 mb-2 uppercase tracking-wider flex items-center gap-1.5">
                          📐 RCPI Generated 2D CAD Site Blueprint & Layout:
                        </p>
                        <img
                          src={m.render2D}
                          alt="2D CAD Site Blueprint"
                          className="w-full max-h-80 object-cover rounded-xl border border-slate-700 shadow-xl"
                        />
                      </div>
                    )}

                    {m.render3D && (
                      <div className="bg-slate-900 p-3 rounded-2xl border border-emerald-500/30">
                        <p className="text-[11px] font-bold text-emerald-400 mb-2 uppercase tracking-wider flex items-center gap-1.5">
                          🌟 RCPI Generated Cinematic 3D Landscape Masterplan:
                        </p>
                        <img
                          src={m.render3D}
                          alt="3D Landscape Masterplan Render"
                          className="w-full max-h-96 object-cover rounded-xl border border-emerald-500/40 shadow-2xl"
                        />
                      </div>
                    )}

                    <div>{m.text}</div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-3 text-xs text-emerald-400 bg-slate-950 p-4 rounded-2xl border border-slate-800 w-fit shadow-inner animate-pulse">
                  <span className="animate-spin text-base">⚡</span> RCPI Engineering Suite is drafting 2D CAD layout, 3D Masterplan render & calculating CPWD BOQ...
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950 flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setRenderMode('2d')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition ${renderMode === '2d' ? 'bg-emerald-500 text-slate-950 border-emerald-400' : 'bg-slate-900 text-slate-300 border-slate-700'}`}
                >
                  2D Blueprint
                </button>
                <button
                  type="button"
                  onClick={() => setRenderMode('3d')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition ${renderMode === '3d' ? 'bg-emerald-500 text-slate-950 border-emerald-400' : 'bg-slate-900 text-slate-300 border-slate-700'}`}
                >
                  3D Photorealistic
                </button>
              </div>

              {sitePhoto && (
                <div className="flex items-center gap-3 bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                  <img src={sitePhoto} alt="Thumbnail" className="h-12 w-12 object-cover rounded-lg border border-slate-700" />
                  <span className="text-xs text-emerald-400 font-semibold">Site Photo attached! Click Generate AI for the selected {renderMode.toUpperCase()} mode analysis.</span>
                  <button
                    type="button"
                    onClick={() => {
                      setSitePhoto(null);
                      setSiteFile(null);
                      setPhotoBase64('');
                    }}
                    className="ml-auto text-xs text-red-400 font-bold px-3 py-1 bg-red-950/40 rounded-lg hover:bg-red-900/50"
                  >
                    Remove
                  </button>
                </div>
              )}

              <div className="flex gap-2.5 items-center">
                <label className="cursor-pointer bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-3 rounded-xl text-xs flex items-center gap-2 border border-slate-700 font-semibold transition-all shadow">
                  📷 Upload Site Photo
                  <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                </label>

                <input
                  type="text"
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAnalyzeSite(e);
                    }
                  }}
                  placeholder="Enter project specifications (e.g. 5000 sqft, 2D layout, 3D mounding, Zoysia grass, BOQ)..."
                  className="flex-grow bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-xs md:text-sm text-white focus:outline-none focus:border-emerald-500 shadow-inner"
                />

                <button
                  type="button"
                  onClick={handleAnalyzeSite}
                  disabled={loading}
                  className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-6 py-3 rounded-xl text-xs md:text-sm transition-all shadow-lg hover:shadow-emerald-500/25"
                >
                  Generate AI
                </button>
              </div>

              <div className="mt-1 rounded-2xl border border-slate-800 bg-slate-950 p-3">
                <form onSubmit={handleChatSubmit} className="flex flex-col gap-2">
                  <label className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">Project Q&A</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask about plants, BOQ, layout, irrigation, or planting logic..."
                      className="flex-grow bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-xs md:text-sm text-white focus:outline-none focus:border-emerald-500 shadow-inner"
                    />
                    <button
                      type="submit"
                      disabled={loading}
                      className="bg-slate-800 hover:bg-slate-700 text-white font-bold px-4 py-3 rounded-xl text-xs border border-slate-700"
                    >
                      Ask AI
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="w-full border-t border-slate-800 bg-slate-950 py-4 px-6 text-center text-xs text-slate-500 flex flex-col sm:flex-row justify-between items-center gap-2">
        <p>© 2026 RCPI INDIA PRIVATE LIMITED. All Global Rights Reserved. | CIN: U45202GJ2021PTC131249</p>
        <p className="text-emerald-400 font-bold">Powered by RCPI INDIA PRIVATE LIMITED</p>
      </footer>
    </div>
  );
}