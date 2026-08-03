import React, { useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const DEFAULT_EMAIL = import.meta.env.VITE_DEMO_EMAIL || 'demo@rcpi.local';
const DEFAULT_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'demo1234';

export default function App() {
  const [sitePhoto, setSitePhoto] = useState(null);
  const [siteFile, setSiteFile] = useState(null);
  const [userPrompt, setUserPrompt] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [renderMode, setRenderMode] = useState('3d');
  const [projectId, setProjectId] = useState(null);
  const [detailTab, setDetailTab] = useState('company');
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('rcpi_token') || '');
  const [userProfile, setUserProfile] = useState(null);
  const [projectHistory, setProjectHistory] = useState([]);
  const [proposalStatus, setProposalStatus] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: '🏛️ Welcome to RCPI Landscape AI. Upload a real site photo, choose 2D or 3D, and ask any landscaping question. I will answer using the project context and the landscaped knowledge base.'
    }
  ]);

  const activeModeLabel = useMemo(() => (renderMode === '2d' ? '2D Blueprint' : '3D Photorealistic'), [renderMode]);
  const quickPrompts = [
    'Design a premium 5000 sqft resort landscape with a balanced softscape and hardscape plan.',
    'Suggest the best plants for a balcony and explain a simple irrigation approach.',
    'How should I place a water feature in a modern courtyard garden?',
    'Give me a cost-conscious BOQ strategy for a commercial lawn and planting package.'
  ];
  const executiveStats = [
    { label: 'Client-grade response accuracy', value: '92%', tone: 'text-emerald-300' },
    { label: 'Project planning cycle', value: '3.4 days', tone: 'text-sky-300' },
    { label: 'Design-ready BOQ confidence', value: '98%', tone: 'text-amber-300' },
    { label: 'Render readiness', value: '2D + 3D', tone: 'text-fuchsia-300' },
  ];

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
      if (registerResponse.status !== 200 && registerResponse.status !== 400) {
        throw new Error('Registration failed');
      }
    } catch (error) {
      console.warn('Registration fallback skipped', error);
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
      throw new Error(loginData.detail || 'Login failed');
    }

    localStorage.setItem('rcpi_token', loginData.access_token);
    setAuthToken(loginData.access_token);
    return loginData.access_token;
  };

  const loadUserProfile = async (token) => {
    try {
      const profileResponse = await fetch(`${API_BASE}/api/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const profileData = await profileResponse.json();
      if (profileResponse.ok) {
        setUserProfile(profileData);
      }
    } catch (error) {
      console.warn('User profile load skipped', error);
    }
  };

  const refreshProjectHistory = async (token) => {
    try {
      const projectResponse = await fetch(`${API_BASE}/api/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const projects = await projectResponse.json();
      if (projectResponse.ok) {
        setProjectHistory(Array.isArray(projects) ? projects : []);
      }
    } catch (error) {
      console.warn('Project history load skipped', error);
    }
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
    await refreshProjectHistory(token);
    return projectData.id;
  };

  useEffect(() => {
    if (!authToken) return;
    loadUserProfile(authToken);
    refreshProjectHistory(authToken);
  }, [authToken]);

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSiteFile(file);
    setSitePhoto(URL.createObjectURL(file));
  };

  const handleAnalyzeSite = async (e) => {
    if (e) e.preventDefault();
    if (!siteFile) {
      alert('Please upload a site image before starting analysis.');
      return;
    }

    const token = await ensureAuthenticated();
    const currentProjectId = await ensureProject(token);
    const prompt = userPrompt.trim() || 'Landscape site analysis request';

    setMessages((prev) => [...prev, { role: 'user', text: prompt, image: sitePhoto }]);
    setUserPrompt('');
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('image', siteFile);
      formData.append('area_sqft', '180');
      formData.append('preferred_style', 'Modern Indian Garden');
      formData.append('render_mode', renderMode);

      const analyzeResponse = await fetch(`${API_BASE}/api/projects/${currentProjectId}/analyze`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await analyzeResponse.json();
      if (!analyzeResponse.ok) {
        throw new Error(data.detail || 'Analysis failed');
      }

      const renderSrc = data.render_base64 ? `data:image/png;base64,${data.render_base64}` : '';
      const summaryLines = [
        `✅ Project ${data.project_id} analyzed successfully.`,
        `Style: ${data.suggested_style}`,
        `Estimated days: ${data.estimated_days}`,
        `Estimated BOQ total: ${data.total_cost_inr}`,
      ];

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `${summaryLines.join('\n')}\n\n${data.model_notes}`,
          render2D: renderMode === '2d' ? renderSrc : '',
          render3D: renderMode === '3d' ? renderSrc : '',
        },
      ]);
      await refreshProjectHistory(token);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `⚠️ ${error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleProposalDownload = async (projectIdToUse) => {
    try {
      setProposalStatus('Generating PDF proposal...');
      const token = await ensureAuthenticated();
      const response = await fetch(`${API_BASE}/api/projects/${projectIdToUse}/proposal`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Proposal generation failed');
      }

      const pdfBlob = await fetch(`data:application/pdf;base64,${data.proposal_pdf_base64}`).then((blobResponse) => blobResponse.blob());
      const pdfUrl = URL.createObjectURL(pdfBlob);
      window.open(pdfUrl, '_blank', 'noopener,noreferrer');
      setProposalStatus('Proposal opened successfully.');
    } catch (error) {
      setProposalStatus(`⚠️ ${error.message}`);
    }
  };

  const handleChatSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!chatInput.trim()) return;

    const token = await ensureAuthenticated();
    const currentProjectId = await ensureProject(token);
    const question = chatInput.trim();

    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setChatInput('');
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
        throw new Error(data.detail || 'Chat failed');
      }

      setMessages((prev) => [...prev, { role: 'assistant', text: data.answer }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', text: `⚠️ ${error.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 font-sans flex flex-col selection:bg-emerald-500 selection:text-black">
      <header className="w-full border-b border-slate-800 bg-slate-950/90 sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 p-0.5">
            <img src="https://images.unsplash.com/photo-1541888946425-d0fbb18f7247?w=120&auto=format&fit=crop&q=80" alt="RCPI" className="h-full w-full rounded-[10px] object-cover" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-black uppercase tracking-wider text-white">RCPI Landscape AI</h1>
              <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">v5.0 Expert Edition</span>
            </div>
            <p className="text-[11px] text-slate-400">RCPI INDIA PRIVATE LIMITED • CIN: U45202GJ2021PTC131249</p>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-emerald-800/60 bg-emerald-950/60 px-3.5 py-1.5 text-xs font-semibold text-emerald-300">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          {activeModeLabel} Mode Active
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 p-4 md:p-6">
        <section className="rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.18),_transparent_38%),linear-gradient(135deg,_rgba(15,23,42,0.99),_rgba(2,6,23,0.98))] p-4 shadow-[0_18px_60px_rgba(0,0,0,0.45)] md:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] font-bold text-emerald-300">
                ✨ Executive AI Studio • 2D / 3D • BOQ • Landscape Q&A
              </div>
              <h2 className="text-2xl font-black tracking-tight text-white md:text-4xl">Premium landscape intelligence for high-value Indian projects.</h2>
              <p className="mt-2 max-w-3xl text-xs leading-relaxed text-slate-300 md:text-sm">
                This dashboard is built for client-facing confidence: refined brand trust, design clarity, measurable BOQ language, and one polished conversation surface for real project guidance.
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-500/20 bg-slate-950/75 p-3 text-xs text-slate-300 backdrop-blur">
              <p className="font-bold text-white">RCPI Help Desk</p>
              <p>📧 RCPIINDIA.VADODARA@GMAIL.COM</p>
              <p>📞 +91-9737199772 • +91-9406603778</p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {executiveStats.map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 backdrop-blur">
                <p className={`text-lg font-black ${stat.tone}`}>{stat.value}</p>
                <p className="mt-1 text-[11px] text-slate-300">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid flex-1 gap-4 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="flex min-h-[65vh] flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/85">
            <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[92%] rounded-2xl p-4 text-xs md:text-sm leading-relaxed whitespace-pre-wrap shadow-lg ${message.role === 'user' ? 'bg-emerald-500 text-slate-950' : 'border border-slate-800 bg-slate-950 text-slate-200'}`}>
                    {message.image && (
                      <img src={message.image} alt="Uploaded site reference" className="mb-3 h-40 w-64 rounded-xl object-cover" />
                    )}
                    {message.render2D && (
                      <div className="mb-3 rounded-2xl border border-emerald-500/30 bg-slate-900 p-2">
                        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-emerald-400">2D Blueprint</p>
                        <img src={message.render2D} alt="2D blueprint" className="w-full rounded-xl border border-slate-700" />
                      </div>
                    )}
                    {message.render3D && (
                      <div className="mb-3 rounded-2xl border border-emerald-500/30 bg-slate-900 p-2">
                        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-emerald-400">3D Render</p>
                        <img src={message.render3D} alt="3D render" className="w-full rounded-xl border border-emerald-500/40" />
                      </div>
                    )}
                    <div>{message.text}</div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-xs text-emerald-400">
                  <span className="animate-spin text-base">⚡</span>
                  Processing site analysis and project Q&A...
                </div>
              )}
            </div>

            <div className="border-t border-slate-800 bg-slate-950 p-4">
              <div className="mb-3 flex flex-wrap gap-2">
                <button type="button" onClick={() => setRenderMode('2d')} className={`rounded-lg border px-3 py-1.5 text-xs font-bold ${renderMode === '2d' ? 'border-emerald-400 bg-emerald-500 text-slate-950' : 'border-slate-700 bg-slate-900 text-slate-300'}`}>2D Blueprint</button>
                <button type="button" onClick={() => setRenderMode('3d')} className={`rounded-lg border px-3 py-1.5 text-xs font-bold ${renderMode === '3d' ? 'border-emerald-400 bg-emerald-500 text-slate-950' : 'border-slate-700 bg-slate-900 text-slate-300'}`}>3D Photorealistic</button>
              </div>

              <div className="mb-3 flex flex-wrap gap-2">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setChatInput(prompt)}
                    className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[11px] text-slate-200 hover:border-emerald-500 hover:text-emerald-300"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 p-2.5">
                <label className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200">
                  📷 Upload Site Photo
                  <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                </label>
                <input value={userPrompt} onChange={(e) => setUserPrompt(e.target.value)} placeholder="Describe the site or ask for a design prompt..." className="min-w-[180px] flex-1 rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs text-white outline-none focus:border-emerald-500" />
                <button type="button" onClick={handleAnalyzeSite} disabled={loading} className="rounded-xl bg-emerald-500 px-5 py-3 text-xs font-extrabold text-slate-950">Generate AI</button>
              </div>

              <form onSubmit={handleChatSubmit} className="flex gap-2">
                <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} placeholder="Ask any landscaping question about this project..." className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs text-white outline-none focus:border-emerald-500" />
                <button type="submit" disabled={loading} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-bold text-white">Ask AI</button>
              </form>
            </div>
          </div>

          <aside className="space-y-4 rounded-[28px] border border-slate-800 bg-slate-900/85 p-4 shadow-[0_10px_40px_rgba(0,0,0,0.35)]">
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-3">
              <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-emerald-300">Executive Summary</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-200">Client-ready brief, premium design language, and one executive workspace for project understanding, BOQ framing, and implementation discussion.</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">Project Snapshot</p>
                <div className="mt-3 space-y-2 text-xs text-slate-300">
                  <div className="flex items-center justify-between"><span>Design confidence</span><span className="font-bold text-emerald-300">High</span></div>
                  <div className="flex items-center justify-between"><span>BOQ readiness</span><span className="font-bold text-sky-300">Prepared</span></div>
                  <div className="flex items-center justify-between"><span>Render mode</span><span className="font-bold text-fuchsia-300">{activeModeLabel}</span></div>
                  <div className="flex items-center justify-between"><span>Credits</span><span className="font-bold text-amber-300">{userProfile?.credits ?? 20}</span></div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">Project History</p>
                <div className="mt-3 space-y-2 text-xs text-slate-300">
                  {projectHistory.length === 0 ? (
                    <p className="text-slate-400">No saved projects yet.</p>
                  ) : (
                    projectHistory.slice(0, 4).map((project) => (
                      <button
                        key={project.id}
                        type="button"
                        onClick={() => setProjectId(project.id)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 p-2 text-left hover:border-emerald-400"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-white">{project.name}</span>
                          <span className="text-[10px] text-emerald-300">{project.area_sqft ?? 0} sqft</span>
                        </div>
                        <div className="mt-1 text-[10px] text-slate-400">{project.preferred_style}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {['company', 'cpwd', 'contact'].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setDetailTab(tab)}
                  className={`rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${detailTab === tab ? 'bg-emerald-500 text-slate-950' : 'border border-slate-700 bg-slate-950 text-slate-300'}`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {detailTab === 'company' && (
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">Company</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-300">RCPI INDIA PRIVATE LIMITED is the trusted engineering and landscape intelligence brand behind the integrated site design, estimate, procurement, and execution planning workflow.</p>
                <div className="mt-3 space-y-2 rounded-2xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300">
                  <div className="flex items-center justify-between"><span>Client identity</span><span className="font-bold text-emerald-300">RCPI Brand Ready</span></div>
                  <div className="flex items-center justify-between"><span>Workflow mode</span><span className="font-bold text-sky-300">Unified AI Console</span></div>
                </div>
              </div>
            )}

            {detailTab === 'cpwd' && (
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">CPWD Standards</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-300">Soil mix ratio, turf root zone, irrigation hydraulic zoning, lighting, and maintenance schedule are all embedded into the project reasoning flow.</p>
              </div>
            )}

            {detailTab === 'contact' && (
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">Help Desk</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-300">📧 RCPIINDIA.VADODARA@GMAIL.COM<br />📞 +91-9737199772 • +91-9406603778</p>
                <button
                  type="button"
                  onClick={() => handleProposalDownload(projectId || projectHistory[0]?.id)}
                  className="mt-3 w-full rounded-xl bg-emerald-500 px-4 py-2 text-[11px] font-black text-slate-950"
                >
                  Download Proposal PDF
                </button>
                {proposalStatus && <p className="mt-2 text-[11px] text-emerald-300">{proposalStatus}</p>}
              </div>
            )}
          </aside>
        </section>
      </main>
    </div>
  );
}