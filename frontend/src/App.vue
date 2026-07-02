<!--
  现代极简工具风（Linear / Vercel 调性）：
  - 亮色中性画布 + 单一 indigo 强调色
  - Hero 顶栏 + 双栏（左：输入/选项/获取，右：结果/复制）
  - 系统字体栈、8dp 间距、1px 细边、轻投影、10px 圆角
  - 复制按钮与歌曲数常驻结果区头部；获取按钮带 loading 态
  功能不变：输入 QQ 音乐歌单链接 → 选项 → 获取 → 复制
-->
<template>
  <div class="app">
    <div class="shell">

      <!-- Hero -->
      <header class="hero">
        <div class="hero-left">
          <p class="kicker">
            {{ state.isEnglish ? 'QQ MUSIC → APPLE / YOUTUBE / SPOTIFY' : 'QQ音乐 → APPLE / YOUTUBE / SPOTIFY' }}
          </p>
          <h1 class="hero-title">
            {{ state.isEnglish ? i18n.title_first.en : i18n.title_first.zh }}
          </h1>
          <p class="hero-sub">
            {{ state.isEnglish ? i18n.title_second.en : i18n.title_second.zh }}
          </p>
        </div>
        <div class="hero-right">
          <a class="github-link" href="https://github.com/mi4646/qqplaylist-export" target="_blank"
             :aria-label="state.isEnglish ? 'GitHub repository' : 'GitHub 仓库'">
            <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" focusable="false">
              <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
          </a>
          <a class="lang-toggle" href="javascript:void(0)" @click="toggleLanguage">
            {{ state.isEnglish ? '中文' : 'English' }}
          </a>
        </div>
      </header>

      <!-- 双栏主体 -->
      <main class="grid">

        <!-- 左：输入 + 选项 + 获取 -->
        <section class="pane">
          <div class="pane-head">
            <h2 class="pane-title">
              {{ state.isEnglish ? 'Input' : '输入' }}
            </h2>
          </div>

          <div class="field">
            <label class="field-label">
              {{ state.isEnglish ? 'Playlist link' : '歌单链接' }}
            </label>
            <el-input v-model="state.link" size="large"
                      :placeholder="state.isEnglish ? i18n.inputPlaceholder.en : i18n.inputPlaceholder.zh"
                      @keyup.enter="throttledFetchLinkDetails"/>
          </div>

          <div class="field">
            <div class="field-label-row">
              <span class="field-label">{{ state.isEnglish ? i18n.songFormat.en : i18n.songFormat.zh }}</span>
            </div>
            <el-radio-group v-model="state.songFormat" class="seg">
              <el-radio-button label="song-singer">
                {{ state.isEnglish ? i18n.formatSongSinger.en : i18n.formatSongSinger.zh }}
              </el-radio-button>
              <el-radio-button label="singer-song">
                {{ state.isEnglish ? i18n.formatSingerSong.en : i18n.formatSingerSong.zh }}
              </el-radio-button>
              <el-radio-button label="song">
                {{ state.isEnglish ? i18n.formatSongOnly.en : i18n.formatSongOnly.zh }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <div class="field">
            <div class="field-label-row">
              <span class="field-label">{{ state.isEnglish ? i18n.songOrder.en : i18n.songOrder.zh }}</span>
            </div>
            <el-radio-group v-model="state.songOrder" class="seg">
              <el-radio-button label="normal">
                {{ state.isEnglish ? i18n.orderNormal.en : i18n.orderNormal.zh }}
              </el-radio-button>
              <el-radio-button label="reverse">
                {{ state.isEnglish ? i18n.orderReverse.en : i18n.orderReverse.zh }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <div class="field field-inline">
            <el-checkbox v-model="state.useDetailedSongName">
              {{ state.isEnglish ? i18n.detailedSongName.en : i18n.detailedSongName.zh }}
            </el-checkbox>
            <el-tooltip
                :content="state.isEnglish ? i18n.detailedSongNameTip.en : i18n.detailedSongNameTip.zh"
                placement="top" effect="light">
              <el-icon class="info-icon"><InfoFilled/></el-icon>
            </el-tooltip>
          </div>

          <el-button type="primary" class="btn-fetch" :loading="state.loading"
                     @click="throttledFetchLinkDetails">
            {{ state.isEnglish ? i18n.fetchSongList.en : i18n.fetchSongList.zh }}
          </el-button>
        </section>

        <!-- 右：结果 -->
        <section class="pane">
          <div class="pane-head pane-head-result">
            <h2 class="pane-title">
              {{ state.isEnglish ? 'Result' : '解析结果' }}
            </h2>
            <div class="result-meta">
              <span class="songs-count" v-show="state.totalCount > 0">
                {{ state.isEnglish ? i18n.parsed.en : i18n.parsed.zh }} {{ state.songsCount }}
                / {{ state.isEnglish ? i18n.total.en : i18n.total.zh }} {{ state.totalCount }}
              </span>
              <el-button class="btn-copy" size="small" :disabled="!state.result" @click="copyResult">
                {{ state.isEnglish ? i18n.copy.en : i18n.copy.zh }}
              </el-button>
              <el-button class="btn-download" size="small" :disabled="!state.result" @click="downloadResult">
                {{ state.isEnglish ? i18n.download.en : i18n.download.zh }}
              </el-button>
            </div>
          </div>

          <el-input type="textarea" v-model="state.result" :rows="16" resize="none"
                    :placeholder="state.isEnglish ? i18n.resultHint.en : i18n.resultHint.zh"/>
        </section>

      </main>

      <footer class="footer">
        <p>
          © 2026 qqplaylist-export · 签名算法移植自
          <a href="https://github.com/Bistutu/GoMusic" target="_blank">GoMusic</a>
        </p>
        <p class="footer-hint">
          {{ state.isEnglish
            ? 'No cache · no database · real-time QQ Music API calls.'
            : '不缓存 · 不落库 · 每次实时调用 QQ 音乐 API。' }}
        </p>
      </footer>

    </div>
  </div>
</template>

<script setup>
import {reactive} from 'vue';
import axios from 'axios';
import {ElMessage} from 'element-plus';
import {isSupportedPlatform, isValidUrl} from "@/utils/utils";
import {sendErrorMessage, sendSuccessMessage} from "@/utils/tip";
import {InfoFilled} from '@element-plus/icons-vue';

const state = reactive({
  link: '',
  result: '',
  isEnglish: false,
  songsCount: 0,
  totalCount: 0,
  playlistName: '',
  useDetailedSongName: false,
  songFormat: 'song-singer',
  songOrder: 'normal',
  loading: false,
});

const i18n = {
  title_first: {en: 'Migrate QQ Music Playlist', zh: '迁移QQ音乐歌单'},
  title_second: {en: 'To Apple / YouTube / Spotify Music', zh: '至 Apple / YouTube / Spotify Music'},
  inputPlaceholder: {
    en: 'Enter a QQ Music playlist link, such as: https://i.y.qq.com/playlist?id=7364061065',
    zh: '输入QQ音乐歌单链接，如：https://i.y.qq.com/playlist?id=7364061065',
  },
  fetchSongList: {en: 'Fetch Song List', zh: '获取歌单'},
  resultHint: {en: 'Result will be displayed here', zh: '结果会显示在这里'},
  copy: {en: 'Copy result', zh: '复制结果'},
  download: {en: 'Download TXT', zh: '下载 TXT'},
  parsed: {en: 'Parsed', zh: '已解析'},
  total: {en: 'Total', zh: '总数'},
  detailedSongName: {
    en: 'use original song name without processing',
    zh: '使用未经处理的原始歌曲名',
  },
  detailedSongNameTip: {
    en: 'By default, this option is unchecked for better compatibility with music platforms. The processed song names have better matching rates when migrating to other platforms.',
    zh: '默认不勾选此项是一种优化选择，处理后的歌曲名在迁移到其他平台时有更好的匹配率',
  },
  emptyPlaylist: {
    en: 'Failed to parse, please check if the playlist is open to public or the link is correct.',
    zh: '解析失败，请检查歌单是否开放访问权限或链接是否正确。',
  },
  songFormat: {en: 'Song Format', zh: '歌曲格式'},
  formatSongSinger: {en: 'Song - Singer', zh: '歌名 - 歌手'},
  formatSingerSong: {en: 'Singer - Song', zh: '歌手 - 歌名'},
  formatSongOnly: {en: 'Song Only', zh: '仅歌名'},
  songOrder: {en: 'Song Order', zh: '歌曲顺序'},
  orderNormal: {en: 'Normal Order', zh: '正序'},
  orderReverse: {en: 'Reverse Order', zh: '倒序'},
};

function reset(msg) {
  sendErrorMessage(msg);
  state.result = "";
  state.songsCount = 0;
  state.totalCount = 0;
  state.playlistName = "";
}

const fetchLinkDetails = async () => {
  state.link = state.link.trim();
  if (!isValidUrl(state.link) || !isSupportedPlatform(state.link)) {
    reset(state.isEnglish ? 'Invalid link, only support QQ Music' : '链接无效，平台仅支持QQ音乐');
    return;
  }
  state.loading = true;
  try {
    const resp = await axios.post('/api/playlist', {
      url: state.link,
      detailed: state.useDetailedSongName,
      format: state.songFormat,
      order: state.songOrder,
    });
    if (!resp.data.songs || resp.data.songs.length === 0 || resp.data.songs_count === 0) {
      reset(state.isEnglish ? i18n.emptyPlaylist.en : i18n.emptyPlaylist.zh);
      return;
    }
    sendSuccessMessage(state.isEnglish ? "Song list fetched successfully" : "歌单获取成功");
    state.result = resp.data.songs.join('\n');
    state.songsCount = resp.data.songs_count;
    state.totalCount = resp.data.total_count;
    state.playlistName = resp.data.name || '';
  } catch (err) {
    console.error(err);
    reset(err.response?.data?.detail || (state.isEnglish ? "Request failed, please try again later~" : "请求失败，请稍后再试~"));
  } finally {
    state.loading = false;
  }
};

const copyResult = () => {
  if (!state.result) {
    ElMessage.error({message: state.isEnglish ? 'No content to copy' : '没有内容可复制', type: 'error'});
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = state.result;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
  ElMessage.success({message: state.isEnglish ? 'Copied to clipboard' : '已复制到剪贴板', type: 'success'});
};

const downloadResult = () => {
  if (!state.result) {
    ElMessage.error({message: state.isEnglish ? 'No content to download' : '没有内容可下载', type: 'error'});
    return;
  }
  // ponytail: 清理 Windows 文件名非法字符，歌单名来自 API 非用户输入但仍可能含特殊符号
  const safeName = (state.playlistName || 'playlist').replace(/[\\/:*?"<>|]/g, '_').trim() || 'playlist';
  const blob = new Blob([state.result], {type: 'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = safeName + '.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const throttle = (fn, delay) => {
  let lastTime = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastTime >= delay) {
      fn.apply(this, args);
      lastTime = now;
    }
  };
};
const throttledFetchLinkDetails = throttle(fetchLinkDetails, 1000);

const toggleLanguage = () => {
  state.isEnglish = !state.isEnglish;
};

// ponytail: 防抖 ResizeObserver，抑制 Element Plus 弹层重排抖动
const debounce = (fn, delay) => {
  let timer = null;
  return function () {
    let context = this;
    let args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      fn.apply(context, args);
    }, delay);
  };
};
const _ResizeObserver = window.ResizeObserver;
window.ResizeObserver = class ResizeObserver extends _ResizeObserver {
  constructor(callback) {
    callback = debounce(callback, 16);
    super(callback);
  }
};
</script>

<style>
/* ── 设计 token ── */
/* ── 设计 token：放 :root，使 ElMessage 等 teleport 到 body 的弹层也能继承 ── */
:root {
  --canvas: #f8fafc;          /* slate-50 页面底 */
  --surface: #ffffff;
  --border: #e2e8f0;          /* slate-200 */
  --border-strong: #cbd5e1;   /* slate-300 */
  --text: #0f172a;            /* slate-900 */
  --text-secondary: #64748b;  /* slate-500 */
  --text-tertiary: #94a3b8;   /* slate-400, placeholder / footer-hint */
  --accent: #409eff;          /* Element Plus primary blue */
  --accent-hover: #337ecc;
  --accent-soft: #ecf5ff;     /* el-color-primary-light-9 */
  --radius: 10px;
  --radius-sm: 8px;
}

/* ponytail: html/body 同底色，避免过度滚动时露出白底与 .app 不一致；margin 归零防止 .app min-height:100vh 叠加默认 margin 溢出 */
html, body { background: var(--canvas); margin: 0; }

.app {
  min-height: 100vh;
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
               'Hiragino Sans GB', 'Microsoft YaHei', Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.shell {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 24px 32px;
}

/* ── Hero ── */
.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  padding-bottom: 32px;
  margin-bottom: 32px;
  border-bottom: 1px solid var(--border);
}
.hero-left { min-width: 0; }
.kicker {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.hero-title {
  margin: 0;
  font-size: 40px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--text);
}
.hero-sub {
  margin: 10px 0 0;
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-secondary);
}
.hero-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.github-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  transition: border-color .15s, color .15s;
}
.github-link:hover { border-color: var(--accent); color: var(--accent); }
.lang-toggle {
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.lang-toggle:hover { border-color: var(--accent); color: var(--accent); }

/* ── 双栏网格 ── */
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: stretch;
}

/* ── 面板卡片 ── */
.pane {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.pane-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary);
}
.result-meta { display: flex; align-items: center; gap: 12px; }
.songs-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-soft);
  border: 1px solid var(--border);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-variant-numeric: tabular-nums;
}

/* ── 字段 ── */
.field { margin-bottom: 20px; }
.field:last-of-type { margin-bottom: 24px; }
.field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}
.field-label-row { display: flex; align-items: center; }
.field-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}
.info-icon { color: var(--text-secondary); cursor: help; font-size: 15px; }

/* ── 按钮 ── */
.btn-fetch {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
}
.btn-copy { font-weight: 500; }

/* ── Element Plus 覆盖 ── */
.app .el-input__wrapper {
  background: var(--surface);
  border: 1px solid var(--border-strong) !important;
  box-shadow: none !important;
  border-radius: var(--radius-sm) !important;
  transition: border-color .15s;
}
.app .el-input__wrapper.is-focus { border-color: var(--accent) !important; }
.app .el-input__inner { color: var(--text); font-size: 14px; }
.app .el-input__inner::placeholder { color: var(--text-tertiary); }

.app .el-textarea__inner {
  border: 1px solid var(--border-strong) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: none !important;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  padding: 12px;
  transition: border-color .15s;
}
.app .el-textarea__inner:focus {
  border-color: var(--accent) !important;
  box-shadow: none !important;
}
.app .el-textarea__inner::placeholder { color: var(--text-tertiary); font-family: inherit; }

.app .el-button {
  border-radius: var(--radius-sm);
  font-weight: 600;
}
.app .el-button--primary {
  background: var(--accent);
  border-color: var(--accent);
}
.app .el-button--primary:hover,
.app .el-button--primary:focus {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}
.app .btn-copy, .app .btn-download {
  background: var(--surface);
  color: var(--text);
  border-color: var(--border-strong);
}
.app .btn-copy:hover, .app .btn-download:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}

/* 分段单选 */
.app .el-radio-button__inner {
  border-color: var(--border-strong) !important;
  color: var(--text-secondary);
  font-weight: 500;
  transition: color .15s, background .15s, border-color .15s;
}
.app .el-radio-button:first-child .el-radio-button__inner {
  border-top-left-radius: var(--radius-sm);
  border-bottom-left-radius: var(--radius-sm);
}
.app .el-radio-button:last-child .el-radio-button__inner {
  border-top-right-radius: var(--radius-sm);
  border-bottom-right-radius: var(--radius-sm);
}
.app .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
  box-shadow: none !important;
}
.app .el-radio-button__inner:hover { color: var(--accent); }

.app .el-checkbox__label {
  font-size: 13px;
  color: var(--text);
}
.app .el-checkbox__inner {
  border-color: var(--border-strong);
  border-radius: 4px;
}
.app .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: var(--accent);
  border-color: var(--accent);
}
.app .el-checkbox__input.is-checked + .el-checkbox__label { color: var(--text); }

/* ElMessage */
.el-message {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border-strong) !important;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08) !important;
}

/* ── footer ── */
.footer {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}
.footer p { margin: 0; }
.footer a { color: var(--accent); text-decoration: none; }
.footer a:hover { text-decoration: underline; }
.footer-hint { margin-top: 4px !important; color: var(--text-tertiary); }

/* ── 响应式：移动端单栏 ── */
@media (max-width: 880px) {
  .shell { padding: 28px 16px 24px; }
  .hero { flex-direction: column; align-items: flex-start; gap: 16px; }
  .hero-title { font-size: 30px; }
  .grid { grid-template-columns: 1fr; }
}

/* ponytail: 小高度视口压缩垂直留白，让页面尽量一屏装下；大屏保持舒展 */
@media (max-height: 800px) {
  .shell { padding: 32px 24px 12px; }
  .hero { padding-bottom: 16px; margin-bottom: 16px; }
  .hero-sub { margin-top: 6px; }
  .footer { margin-top: 16px; padding-top: 12px; }
  .footer-hint { margin-top: 2px !important; }
}
</style>
