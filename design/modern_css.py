LIQUID_GLASS_ULTRA_CSS = """
<style>
:root {
  --lg-bg-1: #07111f;
  --lg-bg-2: #0f2742;
  --lg-bg-3: #173a63;
  --lg-surface: rgba(255, 255, 255, 0.12);
  --lg-surface-strong: rgba(255, 255, 255, 0.18);
  --lg-border: rgba(255, 255, 255, 0.22);
  --lg-text: #f8fbff;
  --lg-text-soft: rgba(248, 251, 255, 0.72);
  --lg-accent: #67e8f9;
  --lg-accent-2: #93c5fd;
  --lg-success: #86efac;
  --lg-warn: #fcd34d;
  --lg-danger: #fca5a5;
  --lg-shadow: 0 24px 80px rgba(2, 8, 23, 0.42);
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(103, 232, 249, 0.15), transparent 28%),
    radial-gradient(circle at 85% 15%, rgba(147, 197, 253, 0.16), transparent 24%),
    radial-gradient(circle at 70% 80%, rgba(125, 211, 252, 0.12), transparent 26%),
    linear-gradient(145deg, var(--lg-bg-1), var(--lg-bg-2) 48%, var(--lg-bg-3));
  color: var(--lg-text);
}

[data-testid="stHeader"] {
  background: rgba(7, 17, 31, 0.35);
  backdrop-filter: blur(4px);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(9, 17, 30, 0.9), rgba(18, 39, 65, 0.78));
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stSidebar"] * {
  color: var(--lg-text);
}

.block-container {
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  max-width: 96rem;
}

[data-testid="stHorizontalBlock"] {
  gap: 1rem;
}

[data-testid="column"] {
  padding-top: 0 !important;
}

h1, h2, h3, h4, h5, h6, p, label, span, div {
  color: var(--lg-text);
}

.lg-page-header {
  position: relative;
  overflow: hidden;
  margin-top: 1.5rem;
  margin-bottom: 0.7rem;
  margin-left: auto;
  padding: 0.18rem 0.42rem;
  width: fit-content;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 11px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.05)),
    rgba(255, 255, 255, 0.05);
  box-shadow: 0 8px 18px rgba(2, 8, 23, 0.14);
  backdrop-filter: blur(14px);
  text-align: right;
  animation: lgFloatIn 0.55s ease-out both;
}

.lg-page-header::before {
  content: "";
  position: absolute;
  inset: -40% auto auto -10%;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(103, 232, 249, 0.18), transparent 68%);
  pointer-events: none;
}

.lg-eyebrow {
  display: none;
}

.lg-page-title {
  margin: 0;
  font-size: 0.36rem;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0;
}

.lg-page-title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.22rem;
}

.lg-page-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--lg-accent), #d8f4ff);
  box-shadow: 0 0 0 0 rgba(103, 232, 249, 0.55);
  animation: lgPulse 2.2s ease-in-out infinite;
}

.lg-page-subtitle {
  display: none;
}

@keyframes lgFloatIn {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes lgPulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(103, 232, 249, 0.45);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 10px rgba(103, 232, 249, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(103, 232, 249, 0);
  }
}

.lg-callout {
  margin-bottom: 1rem;
  padding: 0.95rem 1rem;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(20px);
  color: var(--lg-text-soft);
}

.lg-panel {
  padding: 0.9rem 1rem 0.7rem;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.lg-section-title {
  margin: 0.25rem 0 0.8rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--lg-text);
}

[data-testid="stMetric"],
[data-testid="stFileUploader"],
[data-baseweb="select"],
[data-testid="stDateInputField"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputRootElement"],
[data-testid="stMultiSelect"],
[data-testid="stExpander"],
[data-testid="stTabs"],
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 22px !important;
}

[data-testid="stMetric"] {
  padding: 0.9rem 1rem;
  border: 1px solid rgba(103, 232, 249, 0.2);
  background:
    linear-gradient(135deg, rgba(103, 232, 249, 0.06), rgba(147, 197, 253, 0.04)),
    rgba(255, 255, 255, 0.025);
  box-shadow: 0 10px 28px rgba(2, 8, 23, 0.12);
  backdrop-filter: blur(12px);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

[data-testid="stMetricLabel"] {
  color: var(--lg-text-soft);
}

[data-testid="stMetricValue"] {
  color: var(--lg-text);
}

[data-testid="stMetricDelta"] {
  color: var(--lg-accent) !important;
}

[data-testid="stMetric"]:hover {
  transform: translateY(-2px);
  border-color: rgba(103, 232, 249, 0.45);
  box-shadow: 0 18px 34px rgba(2, 8, 23, 0.18);
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.55rem;
  padding: 0.2rem;
  background: transparent;
  border: none;
  border-radius: 18px;
}

.stTabs [data-baseweb="tab"] {
  height: 42px;
  border-radius: 14px;
  padding: 0 0.95rem;
  color: var(--lg-text-soft);
  background: transparent !important;
}

.stTabs [aria-selected="true"] {
  background: rgba(255, 255, 255, 0.08) !important;
  color: var(--lg-text) !important;
}

[data-testid="stDataFrame"] {
  border: none;
  background: transparent;
  backdrop-filter: none;
  box-shadow: none;
}

[data-testid="stDataFrame"] > div {
  border-radius: 18px;
  border: 1px solid rgba(103, 232, 249, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01)),
    rgba(6, 14, 26, 0.14);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

[data-testid="stDataFrameResizable"] {
  border-radius: 18px;
}

[data-testid="stDataFrame"] > div:hover {
  transform: translateY(-1px);
  border-color: rgba(147, 197, 253, 0.38);
  box-shadow: 0 18px 34px rgba(2, 8, 23, 0.16);
}

[data-testid="stElementContainer"]:has(.vega-embed),
[data-testid="stElementContainer"]:has([data-testid="stDataFrame"]) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
}

[data-testid="stElementContainer"]:has(.vega-embed) {
  margin-bottom: 0.6rem;
}

.vega-embed,
.vega-embed summary,
.vega-embed details {
  background: transparent !important;
}

.vega-embed canvas,
.vega-embed svg {
  background: transparent !important;
}

button[kind="primary"], .stButton > button {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: transparent;
  color: var(--lg-text);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

button[kind="primary"]:hover, .stButton > button:hover {
  transform: translateY(-1px);
  border-color: rgba(103, 232, 249, 0.45);
  box-shadow: 0 14px 28px rgba(2, 8, 23, 0.18);
}

.stAlert {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: transparent;
  backdrop-filter: none;
}

[data-testid="stMarkdownContainer"] code {
  color: #d8f4ff;
}

[data-baseweb="select"] > div,
[data-baseweb="base-input"] > div,
[data-testid="stTextInputRootElement"] > div,
[data-testid="stNumberInputRootElement"] > div,
[data-testid="stDateInputField"] > div,
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  background:
    linear-gradient(135deg, rgba(103, 232, 249, 0.05), rgba(147, 197, 253, 0.03)),
    rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(103, 232, 249, 0.16) !important;
  box-shadow: 0 8px 22px rgba(2, 8, 23, 0.12) !important;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

input, textarea {
  background: transparent !important;
}

[data-baseweb="select"] > div:hover,
[data-baseweb="base-input"] > div:hover,
[data-testid="stTextInputRootElement"] > div:hover,
[data-testid="stNumberInputRootElement"] > div:hover,
[data-testid="stDateInputField"] > div:hover,
[data-testid="stFileUploader"] section:hover,
[data-testid="stFileUploaderDropzone"]:hover {
  transform: translateY(-1px);
  border-color: rgba(103, 232, 249, 0.42) !important;
  box-shadow: 0 14px 28px rgba(2, 8, 23, 0.18) !important;
}

[data-baseweb="select"] > div:focus-within,
[data-baseweb="base-input"] > div:focus-within,
[data-testid="stTextInputRootElement"] > div:focus-within,
[data-testid="stNumberInputRootElement"] > div:focus-within,
[data-testid="stDateInputField"] > div:focus-within {
  border-color: rgba(103, 232, 249, 0.55) !important;
  box-shadow:
    0 0 0 1px rgba(103, 232, 249, 0.16),
    0 14px 30px rgba(2, 8, 23, 0.18) !important;
}

div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li,
div[role="listbox"] {
  background: rgba(9, 17, 30, 0.96) !important;
  color: var(--lg-text) !important;
  border: none !important;
  backdrop-filter: blur(18px);
  box-shadow: none !important;
}

div[role="option"] {
  background: transparent !important;
  color: var(--lg-text) !important;
}

div[role="option"]:hover,
div[role="option"][aria-selected="true"] {
  background: rgba(255, 255, 255, 0.1) !important;
  color: var(--lg-text) !important;
}

[data-baseweb="select"] input {
  color: var(--lg-text) !important;
}

[data-testid="stExpander"] details {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="base-input"] > div {
  background: transparent !important;
}
</style>
"""
