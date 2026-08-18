import { apiClient } from './api.js';

window.APP_BUILD_ID = "UPLOAD_FIX_2026_08_18_01";
console.log("[APP_BUILD]", window.APP_BUILD_ID);

// ================= DOM ELEMENTS =================
// 1. Upload & Video Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const selectBtn = document.getElementById('selectBtn');
const videoPreview = document.getElementById('videoPreview');
const videoFrameWrapper = document.getElementById('videoFrameWrapper');
const maskCanvasLayer = document.getElementById('maskCanvasLayer');
const subtitleLiveOverlay = document.getElementById('subtitleLiveOverlay');
const editorInteractionLayer = document.getElementById('editorInteractionLayer');
const maskRegionsCard = document.getElementById('maskRegionsCard');
const addMaskRegionBtn = document.getElementById('addMaskRegionBtn');
const maskRegionsList = document.getElementById('maskRegionsList');

const videoBadgeName = document.getElementById('videoBadgeName');
const videoBadgeRes = document.getElementById('videoBadgeRes');
const videoBadgeDuration = document.getElementById('videoBadgeDuration');
const videoBadgeFps = document.getElementById('videoBadgeFps');

const videoName = document.getElementById('videoName');
const videoFormat = document.getElementById('videoFormat');
const videoDuration = document.getElementById('videoDuration');
const videoFps = document.getElementById('videoFps');
const videoResolution = document.getElementById('videoResolution');
const videoRatio = document.getElementById('videoRatio');
const videoSize = document.getElementById('videoSize');
const videoUploadDate = document.getElementById('videoUploadDate');

// 2. Progress & Retry Elements
const progressBox = document.getElementById('progressBox');
const progressStatus = document.getElementById('progressStatus');
const progressPercent = document.getElementById('progressPercent');
const progressBarFill = document.getElementById('progressBarFill');

const retryActionBox = document.getElementById('retryActionBox');
const retryErrorMessage = document.getElementById('retryErrorMessage');
const btnRetryFailed = document.getElementById('btnRetryFailed');
const btnRerunAll = document.getElementById('btnRerunAll');

// 3. Batch Queue Bar Elements
const batchQueueBar = document.getElementById('batchQueueBar');
const queueCountBadge = document.getElementById('queueCountBadge');
const queueTotalProgress = document.getElementById('queueTotalProgress');
const queuePillsList = document.getElementById('queuePillsList');

// 4. Stepper & Step Pills
const stepUpload = document.getElementById('stepUpload');
const stepExtract = document.getElementById('stepExtract');
const stepWhisper = document.getElementById('stepWhisper');
const stepTranslate = document.getElementById('stepTranslate');
const stepTTS = document.getElementById('stepTTS');
const stepRender = document.getElementById('stepRender');

const stepperItem1 = document.getElementById('stepperItem1');
const stepperItem2 = document.getElementById('stepperItem2');
const stepperItem3 = document.getElementById('stepperItem3');
const stepperItem4 = document.getElementById('stepperItem4');
const stepperItem5 = document.getElementById('stepperItem5');
const stepperItem6 = document.getElementById('stepperItem6');

const stepperCheck1 = document.getElementById('stepperCheck1');
const stepperCheck2 = document.getElementById('stepperCheck2');
const stepperCheck3 = document.getElementById('stepperCheck3');
const stepperCheck4 = document.getElementById('stepperCheck4');
const stepperCheck5 = document.getElementById('stepperCheck5');
const stepperCheck6 = document.getElementById('stepperCheck6');

// 5. Configuration Controls (Dịch thuật & Gemini Key Management)
const sourceLangSelect = document.getElementById('sourceLangSelect');
const targetLangSelect = document.getElementById('targetLangSelect');
const translationStyleSelect = document.getElementById('translationStyleSelect');

const geminiKeyStatusBox = document.getElementById('geminiKeyStatusBox');
const geminiStatusText = document.getElementById('geminiStatusText');
const btnChangeGeminiKey = document.getElementById('btnChangeGeminiKey');
const btnDeleteGeminiKey = document.getElementById('btnDeleteGeminiKey');
const geminiKeyInputBox = document.getElementById('geminiKeyInputBox');
const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
const btnSaveGeminiKey = document.getElementById('btnSaveGeminiKey');
const btnCancelGeminiKey = document.getElementById('btnCancelGeminiKey');

const voiceSelect = document.getElementById('voiceSelect');
const previewVoiceBtn = document.getElementById('previewVoiceBtn');
const resetConfigBtn = document.getElementById('resetConfigBtn');

const speedRateRange = document.getElementById('speedRateRange');
const speedRateValue = document.getElementById('speedRateValue');
const pitchRange = document.getElementById('pitchRange');
const pitchValue = document.getElementById('pitchValue');
const voiceVolumeRange = document.getElementById('voiceVolumeRange');
const voiceVolumeValue = document.getElementById('voiceVolumeValue');
const bgVolumeRange = document.getElementById('bgVolumeRange');
const bgVolumeValue = document.getElementById('bgVolumeValue');

const keepBgAudioCheckbox = document.getElementById('keepBgAudioCheckbox');
const resolutionSelect = document.getElementById('resolutionSelect');
const formatSelect = document.getElementById('formatSelect');

// 6. Subtitle Style Controls (Phase 5 & Direct Manipulation)
const subtitleStyleCard = document.getElementById('subtitleStyleCard');
const subFontFamily = document.getElementById('subFontFamily');
const subTextColor = document.getElementById('subTextColor');
const subTextColorLabel = document.getElementById('subTextColorLabel');
const subOutlineColor = document.getElementById('subOutlineColor');
const subOutlineColorLabel = document.getElementById('subOutlineColorLabel');
const subFontSize = document.getElementById('subFontSize');
const subOutlineWidth = document.getElementById('subOutlineWidth');
const subOutlineWidthValue = document.getElementById('subOutlineWidthValue');
const subBoldCheckbox = document.getElementById('subBoldCheckbox');
const subShadowCheckbox = document.getElementById('subShadowCheckbox');
const resetSubStyleBtn = document.getElementById('resetSubStyleBtn');

// 7. Processing Options Checkboxes & Sub-controls
const optSTT = document.getElementById('optSTT');
const whisperModelSelect = document.getElementById('whisperModelSelect');
const whisperModelSubOption = document.getElementById('whisperModelSubOption');
const optTranslate = document.getElementById('optTranslate');
const optTTS = document.getElementById('optTTS');
const optSubtitle = document.getElementById('optSubtitle');
const subModeSubOption = document.getElementById('subModeSubOption');
const subModeSelect = document.getElementById('subModeSelect');
const optRender = document.getElementById('optRender');

// 8. Unified Primary CTA Button
const runPipelineBtn = document.getElementById('runPipelineBtn');

// 9. Center Column Logs
const logTableBody = document.getElementById('logTableBody');

// 10. Subtitles / Transcript List
const downloadOriginalSrtBtn = document.getElementById('downloadOriginalSrtBtn');
const downloadTranslatedSrtBtn = document.getElementById('downloadTranslatedSrtBtn');
const refreshSubsBtn = document.getElementById('refreshSubsBtn');
const tabOriginal = document.getElementById('tabOriginal');
const tabTranslated = document.getElementById('tabTranslated');
const autoScrollCheckbox = document.getElementById('autoScrollCheckbox');
const subSearchInput = document.getElementById('subSearchInput');
const transcriptList = document.getElementById('transcriptList');
const totalSubsCount = document.getElementById('totalSubsCount');
const avgCpsCount = document.getElementById('avgCpsCount');
const maxCpsCount = document.getElementById('maxCpsCount');

// 11. Final Video Output Card & Batch Results
const finalVideoStatusBadge = document.getElementById('finalVideoStatusBadge');
const finalVideoEmpty = document.getElementById('finalVideoEmpty');
const finalVideoContent = document.getElementById('finalVideoContent');
const finalVideoPlayer = document.getElementById('finalVideoPlayer');
const finalThumbDuration = document.getElementById('finalThumbDuration');
const finalVideoName = document.getElementById('finalVideoName');
const finalVideoRes = document.getElementById('finalVideoRes');
const finalVideoFormat = document.getElementById('finalVideoFormat');
const finalVideoSize = document.getElementById('finalVideoSize');
const finalVideoDuration = document.getElementById('finalVideoDuration');
const finalVideoDate = document.getElementById('finalVideoDate');
const downloadVideoBtn = document.getElementById('downloadVideoBtn');
const downloadSrtBtn = document.getElementById('downloadSrtBtn');
const btnNewVideo = document.getElementById('btnNewVideo');
const btnHeaderNewVideo = document.getElementById('btnHeaderNewVideo');
const batchResultsWrapper = document.getElementById('batchResultsWrapper');
const batchResultsList = document.getElementById('batchResultsList');

// 12. History Drawer Elements
const btnOpenHistory = document.getElementById('btnOpenHistory');
const btnCloseHistory = document.getElementById('btnCloseHistory');
const historyDrawer = document.getElementById('historyDrawer');
const historyDrawerBackdrop = document.getElementById('historyDrawerBackdrop');
const historySearchInput = document.getElementById('historySearchInput');
const historyListContainer = document.getElementById('historyListContainer');

// 13. Alerts & Toast
const systemAlert = document.getElementById('systemAlert');
const systemAlertText = document.getElementById('systemAlertText');
const toastContainer = document.getElementById('toastContainer');

// ================= APPLICATION CENTRAL STATE =================
let workspaceGeneration = 0; // Generation token to invalidate stale responses (Section 5)
let workspaceMode = 'no_job'; // 'no_job' | 'job' | 'batch' (Section 10)
let isGeminiConfigured = false; // State of Gemini API Key configuration
let currentJob = null;
let currentJobId = null;
let currentBatchId = null;
let batchJobs = []; // Array of Job items in current batch
let activeJobIndex = 0;
let isProcessing = false;
let previewAudioObj = null;
let currentSegments = [];
let translatedSegments = [];
let subtitleData = [];
let jobArtifacts = null;
let pipelineState = null;
let progressState = 0;
let errorState = null;
let retryState = null;
let currentOutput = null;

let activeSubtitleTab = 'translated'; // 'original' | 'translated'
let allHistoryJobs = [];
let subtitleLayout = {
  x: 0.50,
  y: 0.88,
  width: 0.70,
  height: 0.15,
};
let subtitlePosition = { x: 0.50, y: 0.88 }; // Backward compatibility alias
let maskRegions = []; // Array of MaskRegion items
let selectedObjectId = 'subtitle'; // 'subtitle' | mask.id

// Poller State
let activePollTimer = null;
let activePollJobId = null;
let activeBatchPollTimer = null;

/**
 * Xóa sạch toàn bộ Central State Data Model trước khi render lại DOM
 */
function clearCentralJobState() {
  currentJob = null;
  currentJobId = null;
  currentBatchId = null;
  batchJobs = [];
  activeJobIndex = 0;
  currentSegments = [];
  translatedSegments = [];
  subtitleData = [];
  jobArtifacts = null;
  pipelineState = null;
  progressState = 0;
  errorState = null;
  retryState = null;
  currentOutput = null;
  isProcessing = false;

  if (previewAudioObj) {
    previewAudioObj.pause();
    previewAudioObj = null;
  }
}

/**
 * Guard ở tất cả Job-specific Renderers & Async Callbacks (Section 3 & 4):
 * Bất kỳ renderer nào khi workspaceMode === 'no_job' hoặc currentJobId === null đều KHÔNG ĐƯỢC PHÉP thực thi.
 */
function canApplyJobPayload(jobId, generation) {
  if (workspaceMode === 'no_job' || currentJobId === null) {
    return false;
  }
  if (jobId && currentJobId && jobId !== currentJobId) {
    return false;
  }
  if (generation !== undefined && generation !== workspaceGeneration) {
    return false;
  }
  return true;
}

const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.mkv', '.webm'];

const STAGE_ORDER = [
  'upload',
  'metadata',
  'extract_audio',
  'stt',
  'translation',
  'tts',
  'audio_sync',
  'subtitle',
  'render',
];

const STAGE_CONFIG = {
  upload: { label: 'Tải video lên', icon: '📤' },
  metadata: { label: 'Đọc metadata video', icon: 'ℹ️' },
  extract_audio: { label: 'Tách giọng & trích xuất Dual Audio', icon: '🎧' },
  stt: { label: 'Whisper STT - Nhận dạng giọng nói', icon: '🎙️' },
  translation: { label: 'Gemini AI - Dịch thuật ngữ cảnh', icon: '🌐' },
  tts: { label: 'AI Voice TTS - Tổng hợp giọng đọc', icon: '🔊' },
  audio_sync: { label: 'Đồng bộ & Lồng tiếng timeline', icon: '⏱️' },
  subtitle: { label: 'Tạo phụ đề chuẩn (.SRT & .ASS)', icon: '📝' },
  render: { label: 'Render Video hoàn chỉnh (H.264 + AAC 48kHz)', icon: '🎬' },
};

// ================= UTILITIES & HELPERS =================
function showToast(message, type = 'success') {
  if (!toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'error' : ''}`;
  toast.innerHTML = `<span>${type === 'error' ? '❌' : '✓'}</span><span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => {
      if (toast && typeof toast.remove === 'function') {
        toast.remove();
      } else if (toast && toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, 3500);
}

function formatDuration(seconds) {
  if (!seconds || isNaN(seconds)) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatTime(isoString) {
  if (!isoString) return '--:--:--';
  try {
    const d = new Date(isoString);
    return d.toTimeString().split(' ')[0];
  } catch (e) {
    return '--:--:--';
  }
}

function formatDurationMs(ms) {
  if (!ms || ms <= 0) return '00:00:00';
  const totalSecs = Math.floor(ms / 1000);
  const hours = Math.floor(totalSecs / 3600);
  const mins = Math.floor((totalSecs % 3600) / 60);
  const secs = totalSecs % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// ================= INITIALIZATION & RESTORE =================
async function initApp() {
  // 1. Critical event listeners & direct manipulation handlers MUST bind first
  try {
    initEventListeners();
    updateSubtitleVisibilityAndPreview();
  } catch (e) {
    console.error('[INIT_CRITICAL_LISTENERS_ERROR]', e);
  }

  // 2. Health check (non-blocking)
  try {
    const health = await apiClient.checkHealth();
    if (health && health.status === 'healthy') {
      if (systemAlertText) systemAlertText.textContent = 'Hệ thống sẵn sàng: FFmpeg, Faster-Whisper, Gemini AI, Edge-TTS & ASS Burn-in đã kích hoạt.';
    } else {
      if (systemAlertText) systemAlertText.textContent = `Cảnh báo: ${(health && health.message) || 'Một số module chưa sẵn sàng'}`;
      if (systemAlert) systemAlert.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    }
  } catch (e) {
    console.warn('Lỗi kiểm tra hệ thống:', e);
  }

  // 3. Optional service status (Gemini API Key) - Non-blocking
  try {
    await loadGeminiStatus();
  } catch (e) {
    console.warn('Lỗi tải trạng thái Gemini:', e);
  }

  // 4. Restore Job hoặc Batch sau khi F5 (CASE A: Đang xem Job hợp lệ / CASE B: NO_JOB)
  try {
    const savedWorkspaceMode = localStorage.getItem('workspace_mode');
    const savedBatchId = localStorage.getItem('last_batch_id');
    const savedJobId = localStorage.getItem('last_job_id');

    if (savedWorkspaceMode === 'no_job') {
      resetWorkspaceToNoJob();
    } else if (savedWorkspaceMode === 'batch' && savedBatchId) {
      await restoreBatchState(savedBatchId);
    } else if (savedJobId) {
      await restoreJobState(savedJobId);
    } else {
      resetWorkspaceToNoJob();
    }
  } catch (e) {
    console.error('[INIT_WORKSPACE_RESTORE_ERROR]', e);
    resetWorkspaceToNoJob();
  }
}

// Bootstrap on DOM Ready or Immediately if already loaded (Fix for deferred ES Modules)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

// ================= GEMINI API KEY MANAGEMENT =================
async function loadGeminiStatus() {
  try {
    const res = await apiClient.getGeminiStatus();
    isGeminiConfigured = Boolean(res && res.configured);
    if (res && res.configured) {
      if (geminiKeyStatusBox) geminiKeyStatusBox.style.display = 'flex';
      if (geminiKeyInputBox) geminiKeyInputBox.style.display = 'none';
      if (geminiStatusText) {
        geminiStatusText.textContent = 'Gemini API: Đã cấu hình';
        if (res.source === 'env') {
          geminiStatusText.textContent = 'Gemini API: Cấu hình qua .env';
        }
      }
    } else {
      if (geminiKeyStatusBox) geminiKeyStatusBox.style.display = 'none';
      if (geminiKeyInputBox) geminiKeyInputBox.style.display = 'block';
      if (btnCancelGeminiKey) btnCancelGeminiKey.style.display = 'none';
    }
  } catch (e) {
    console.warn('Lỗi kiểm tra trạng thái Gemini:', e);
  }
}

async function handleSaveGeminiKey() {
  const key = (geminiApiKeyInput.value || '').trim();
  if (!key) {
    showToast('Vui lòng nhập Gemini API Key (bắt đầu bằng AIza)', 'error');
    return;
  }

  btnSaveGeminiKey.disabled = true;
  btnSaveGeminiKey.innerHTML = '<span>⏳</span> Đang lưu...';

  try {
    const res = await apiClient.saveGeminiKey(key);
    geminiApiKeyInput.value = '';
    showToast('Đã lưu trữ và kích hoạt Gemini API Key thành công.');
    await loadGeminiStatus();
  } catch (err) {
    showToast(err.message || 'Lỗi khi lưu Gemini API Key', 'error');
  } finally {
    btnSaveGeminiKey.disabled = false;
    btnSaveGeminiKey.innerHTML = 'Lưu Key';
  }
}

async function handleDeleteGeminiKey() {
  if (confirm('Bạn có chắc muốn xóa Gemini API Key đã lưu?')) {
    try {
      await apiClient.deleteGeminiKey();
      showToast('Đã xóa Gemini API Key khỏi hệ thống.');
      await loadGeminiStatus();
    } catch (err) {
      showToast('Lỗi khi xóa API Key', 'error');
    }
  }
}

// ================= EVENT LISTENERS =================
function initEventListeners() {
  // Dropzone & File Selection (Hỗ trợ 1-5 file video)
  if (selectBtn) {
    selectBtn.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }
  if (dropzone) {
    dropzone.addEventListener('click', (e) => {
      if (e.target !== selectBtn && (!selectBtn || !selectBtn.contains(e.target))) {
        if (fileInput) fileInput.click();
      }
    });

    ['dragenter', 'dragover'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
      });
    });

    dropzone.addEventListener('drop', async (e) => {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        try {
          await handleFilesSelected(Array.from(e.dataTransfer.files));
        } catch (err) {
          console.error('[UPLOAD_DROP_ERROR]', err);
          showToast('Lỗi khi tải file: ' + (err.message || err), 'error');
        }
      }
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      if (e.target.files && e.target.files.length > 0) {
        const files = Array.from(e.target.files);
        fileInput.value = ''; // Reset input để chọn lại cùng 1 file vẫn trigger change
        try {
          await handleFilesSelected(files);
        } catch (err) {
          console.error('[UPLOAD_CHANGE_ERROR]', err);
          showToast('Lỗi khi tải file: ' + (err.message || err), 'error');
        }
      }
    });
  }

  // Slider Badges
  if (speedRateRange && speedRateValue) {
    speedRateRange.addEventListener('input', () => {
      const val = parseInt(speedRateRange.value);
      speedRateValue.textContent = val >= 0 ? `+${val}%` : `${val}%`;
    });
  }

  if (pitchRange && pitchValue) {
    pitchRange.addEventListener('input', () => {
      const val = parseInt(pitchRange.value);
      pitchValue.textContent = val >= 0 ? `+${val}Hz` : `${val}Hz`;
    });
  }

  if (voiceVolumeRange && voiceVolumeValue) {
    voiceVolumeRange.addEventListener('input', () => {
      voiceVolumeValue.textContent = `${voiceVolumeRange.value}%`;
    });
  }

  if (bgVolumeRange && bgVolumeValue) {
    bgVolumeRange.addEventListener('input', () => {
      bgVolumeValue.textContent = `${bgVolumeRange.value}%`;
    });
  }

  // Gemini API Key Buttons
  if (btnSaveGeminiKey) btnSaveGeminiKey.addEventListener('click', handleSaveGeminiKey);
  if (btnChangeGeminiKey) {
    btnChangeGeminiKey.addEventListener('click', () => {
      if (geminiKeyStatusBox) geminiKeyStatusBox.style.display = 'none';
      if (geminiKeyInputBox) geminiKeyInputBox.style.display = 'block';
      if (btnCancelGeminiKey) btnCancelGeminiKey.style.display = 'inline-block';
      if (geminiApiKeyInput) geminiApiKeyInput.focus();
    });
  }
  if (btnCancelGeminiKey) {
    btnCancelGeminiKey.addEventListener('click', () => {
      if (geminiKeyInputBox) geminiKeyInputBox.style.display = 'none';
      if (geminiKeyStatusBox) geminiKeyStatusBox.style.display = 'flex';
      if (geminiApiKeyInput) geminiApiKeyInput.value = '';
    });
  }
  if (btnDeleteGeminiKey) btnDeleteGeminiKey.addEventListener('click', handleDeleteGeminiKey);

  // Subtitle Toggle & Subtitle Mode (Requirements 15, 16, 17, 18)
  if (optSubtitle) {
    optSubtitle.addEventListener('change', () => {
      updateSubtitleVisibilityAndPreview();
    });
  }

  if (subModeSelect) {
    subModeSelect.addEventListener('change', () => {
      updateSubtitleVisibilityAndPreview();
    });
  }

  // Subtitle Style Realtime Controls & Live Preview Sync (Requirements 1-4, 20-21)
  [
    subFontFamily,
    subTextColor,
    subOutlineColor,
    subFontSize,
    subOutlineWidth,
    subBoldCheckbox,
    subShadowCheckbox,
  ].forEach((elem) => {
    if (!elem) return;
    elem.addEventListener('input', () => {
      if (elem === subTextColor && subTextColorLabel) subTextColorLabel.textContent = subTextColor.value.toUpperCase();
      if (elem === subOutlineColor && subOutlineColorLabel) subOutlineColorLabel.textContent = subOutlineColor.value.toUpperCase();
      if (elem === subOutlineWidth && subOutlineWidthValue) subOutlineWidthValue.textContent = `${subOutlineWidth.value}px`;
      updateSubtitleOverlayStyles();
    });
  });

  if (resetSubStyleBtn) {
    resetSubStyleBtn.addEventListener('click', () => {
      if (subFontFamily) subFontFamily.value = 'Arial';
      if (subTextColor) {
        subTextColor.value = '#ffffff';
        if (subTextColorLabel) subTextColorLabel.textContent = '#FFFFFF';
      }
      if (subOutlineColor) {
        subOutlineColor.value = '#000000';
        if (subOutlineColorLabel) subOutlineColorLabel.textContent = '#000000';
      }
      if (subFontSize) subFontSize.value = 36;
      if (subOutlineWidth) {
        subOutlineWidth.value = 2.5;
        if (subOutlineWidthValue) subOutlineWidthValue.textContent = '2.5px';
      }
      if (subBoldCheckbox) subBoldCheckbox.checked = true;
      if (subShadowCheckbox) subShadowCheckbox.checked = true;
      subtitleLayout = { x: 0.50, y: 0.88, width: 0.70, height: 0.15 };
      subtitlePosition = { x: 0.50, y: 0.88 };
      renderCanvasOverlays();
      showToast('Đã khôi phục style phụ đề mặc định (x=50%, y=88%, w=70%, h=15%)');
    });
  }

  // Synchronize Live Subtitle Overlay on Video Timeupdate
  if (videoPreview) {
    videoPreview.addEventListener('timeupdate', () => {
      updateSubtitleOverlayText();
    });
  }

  // Khởi tạo các sự kiện kéo thả & resize trên Video Canvas Editor
  initCanvasEditorEvents();

  // Whisper STT Checkbox dependency
  if (optSTT) {
    optSTT.addEventListener('change', () => {
      if (optSTT.checked) {
        if (whisperModelSelect) whisperModelSelect.disabled = false;
        if (whisperModelSubOption) {
          whisperModelSubOption.style.opacity = '1';
          whisperModelSubOption.style.pointerEvents = 'auto';
        }
      } else {
        if (whisperModelSelect) whisperModelSelect.disabled = true;
        if (whisperModelSubOption) {
          whisperModelSubOption.style.opacity = '0.4';
          whisperModelSubOption.style.pointerEvents = 'none';
        }
      }
    });
  }

  // Voice Preview
  if (previewVoiceBtn) previewVoiceBtn.addEventListener('click', handlePreviewVoice);

  // Reset Config
  if (resetConfigBtn) {
    resetConfigBtn.addEventListener('click', () => {
      if (sourceLangSelect) sourceLangSelect.value = 'auto';
      if (targetLangSelect) targetLangSelect.value = 'vi';
      if (translationStyleSelect) translationStyleSelect.value = 'movie_review_spoken_vi';
      if (voiceSelect) voiceSelect.value = 'vi-VN-NamMinhNeural_tiktok_review';
      if (speedRateRange) speedRateRange.value = 15;
      if (speedRateValue) speedRateValue.textContent = '+15%';
      if (pitchRange) pitchRange.value = 2;
      if (pitchValue) pitchValue.textContent = '+2Hz';
      if (voiceVolumeRange) voiceVolumeRange.value = 120;
      if (voiceVolumeValue) voiceVolumeValue.textContent = '120%';
      if (bgVolumeRange) bgVolumeRange.value = 15;
      if (bgVolumeValue) bgVolumeValue.textContent = '15%';
      showToast('Đã đặt lại cấu hình lồng tiếng');
    });
  }

  // Primary Action Button (Unified Run Pipeline)
  if (runPipelineBtn) runPipelineBtn.addEventListener('click', handleRunPipeline);

  // Retry Handlers (Phase 1)
  if (btnRetryFailed) btnRetryFailed.addEventListener('click', () => handleRetry(true));
  if (btnRerunAll) btnRerunAll.addEventListener('click', () => handleRetry(false));

  // New Video Workflow (Phase 4)
  if (btnNewVideo) btnNewVideo.addEventListener('click', handleNewVideoWorkflow);
  if (btnHeaderNewVideo) btnHeaderNewVideo.addEventListener('click', handleNewVideoWorkflow);

  // Subtitle Tabs & Search
  if (tabOriginal) {
    tabOriginal.addEventListener('click', () => {
      activeSubtitleTab = 'original';
      tabOriginal.classList.add('active');
      if (tabTranslated) tabTranslated.classList.remove('active');
      renderSubtitles();
    });
  }

  if (tabTranslated) {
    tabTranslated.addEventListener('click', () => {
      activeSubtitleTab = 'translated';
      tabTranslated.classList.add('active');
      if (tabOriginal) tabOriginal.classList.remove('active');
      renderSubtitles();
    });
  }

  if (subSearchInput) subSearchInput.addEventListener('input', () => renderSubtitles());
  if (refreshSubsBtn) {
    refreshSubsBtn.addEventListener('click', () => {
      if (currentJobId && workspaceMode === 'job') {
        const curGen = workspaceGeneration;
        const targetJobId = currentJobId;
        apiClient.getJob(targetJobId).then((job) => {
          if (!canApplyJobPayload(targetJobId, curGen)) return;
          if (job && job.segments) {
            currentSegments = job.segments;
            translatedSegments = job.segments.filter((s) => s.translated_text);
            subtitleData = job.segments;
            renderSubtitles();
            showToast('Đã làm mới danh sách phụ đề');
          }
        });
      }
    });
  }

  // History Drawer (Phase 2)
  if (btnOpenHistory) btnOpenHistory.addEventListener('click', openHistoryDrawer);
  if (btnCloseHistory) btnCloseHistory.addEventListener('click', closeHistoryDrawer);
  if (historyDrawerBackdrop) historyDrawerBackdrop.addEventListener('click', closeHistoryDrawer);
  if (historySearchInput) historySearchInput.addEventListener('input', renderHistoryList);
}

// ================= DIRECT MANIPULATION CANVAS EDITOR (SUBTITLES & MASK REGIONS) =================
let activePointerId = null;
let activeDragMode = null; // 'move' | 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'
let activeDragTargetId = null; // 'subtitle' | mask.id
let dragStartPointerX = 0;
let dragStartPointerY = 0;
let initialTargetGeom = { x: 0, y: 0, width: 0, height: 0 };

function initCanvasEditorEvents() {
  if (!editorInteractionLayer) return;

  // Add Mask Button
  if (addMaskRegionBtn) {
    addMaskRegionBtn.addEventListener('click', () => {
      addNewMaskRegion();
    });
  }

  // Pointer Down on Editor Layer (Event delegation for boxes and handles)
  editorInteractionLayer.addEventListener('pointerdown', (e) => {
    const handle = e.target.closest('.resize-handle');
    const box = e.target.closest('.editor-bounding-box');
    if (!box) return;

    const targetId = box.dataset.objectId;
    if (!targetId) return;

    // Check if mask is locked
    if (targetId.startsWith('mask_')) {
      const maskObj = maskRegions.find((m) => m.id === targetId);
      if (maskObj && maskObj.locked) {
        selectedObjectId = targetId;
        renderCanvasOverlays();
        renderMaskRegionsList();
        return;
      }
    }

    e.preventDefault();
    e.stopPropagation();

    selectedObjectId = targetId;
    activePointerId = e.pointerId;
    dragStartPointerX = e.clientX;
    dragStartPointerY = e.clientY;

    if (handle) {
      activeDragMode = handle.dataset.handle; // 'nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'
    } else {
      activeDragMode = 'move';
    }

    activeDragTargetId = targetId;

    // Store initial geometry
    if (targetId === 'subtitle') {
      initialTargetGeom = {
        x: subtitleLayout.x,
        y: subtitleLayout.y,
        width: subtitleLayout.width,
        height: subtitleLayout.height,
      };
    } else {
      const maskObj = maskRegions.find((m) => m.id === targetId);
      if (maskObj) {
        initialTargetGeom = {
          x: maskObj.x,
          y: maskObj.y,
          width: maskObj.width,
          height: maskObj.height,
        };
      }
    }

    try {
      editorInteractionLayer.setPointerCapture(e.pointerId);
    } catch (err) {}

    window.addEventListener('pointermove', onPointerMoveCanvas);
    window.addEventListener('pointerup', onPointerUpCanvas);
    window.addEventListener('pointercancel', onPointerUpCanvas);

    renderCanvasOverlays();
    renderMaskRegionsList();
  });
}

function onPointerMoveCanvas(e) {
  if (!activeDragMode || !activeDragTargetId) return;

  const rect = videoFrameWrapper ? videoFrameWrapper.getBoundingClientRect() : { width: 640, height: 360 };
  const dx = (e.clientX - dragStartPointerX) / Math.max(1, rect.width);
  const dy = (e.clientY - dragStartPointerY) / Math.max(1, rect.height);

  if (activeDragTargetId === 'subtitle') {
    // Subtitle object (uses center x, y and normalized width, height)
    const initW = initialTargetGeom.width;
    const initH = initialTargetGeom.height;
    const initL = initialTargetGeom.x - initW / 2;
    const initT = initialTargetGeom.y - initH / 2;
    const initR = initL + initW;
    const initB = initT + initH;

    if (activeDragMode === 'move') {
      const newX = Math.max(initW / 2, Math.min(1.0 - initW / 2, initialTargetGeom.x + dx));
      const newY = Math.max(initH / 2, Math.min(1.0 - initH / 2, initialTargetGeom.y + dy));
      subtitleLayout.x = Math.round(newX * 10000) / 10000;
      subtitleLayout.y = Math.round(newY * 10000) / 10000;
      subtitlePosition.x = subtitleLayout.x;
      subtitlePosition.y = subtitleLayout.y;
    } else {
      // 8-point resize handles
      let newL = initL;
      let newT = initT;
      let newR = initR;
      let newB = initB;

      if (['w', 'nw', 'sw'].includes(activeDragMode)) {
        newL = Math.max(0.0, Math.min(initR - 0.10, initL + dx));
      }
      if (['e', 'ne', 'se'].includes(activeDragMode)) {
        newR = Math.max(initL + 0.10, Math.min(1.0, initR + dx));
      }
      if (['n', 'nw', 'ne'].includes(activeDragMode)) {
        newT = Math.max(0.0, Math.min(initB - 0.05, initT + dy));
      }
      if (['s', 'sw', 'se'].includes(activeDragMode)) {
        newB = Math.max(initT + 0.05, Math.min(1.0, initB + dy));
      }

      const newW = Math.max(0.10, newR - newL);
      const newH = Math.max(0.05, newB - newT);
      const newX = newL + newW / 2;
      const newY = newT + newH / 2;

      subtitleLayout.x = Math.round(newX * 10000) / 10000;
      subtitleLayout.y = Math.round(newY * 10000) / 10000;
      subtitleLayout.width = Math.round(newW * 10000) / 10000;
      subtitleLayout.height = Math.round(newH * 10000) / 10000;
      subtitlePosition.x = subtitleLayout.x;
      subtitlePosition.y = subtitleLayout.y;
    }
  } else {
    // Mask object (uses top-left x, y and normalized width, height)
    const maskObj = maskRegions.find((m) => m.id === activeDragTargetId);
    if (!maskObj || maskObj.locked) return;

    const initW = initialTargetGeom.width;
    const initH = initialTargetGeom.height;
    const initL = initialTargetGeom.x;
    const initT = initialTargetGeom.y;
    const initR = initL + initW;
    const initB = initT + initH;

    if (activeDragMode === 'move') {
      const newX = Math.max(0.0, Math.min(1.0 - initW, initL + dx));
      const newY = Math.max(0.0, Math.min(1.0 - initH, initT + dy));
      maskObj.x = Math.round(newX * 10000) / 10000;
      maskObj.y = Math.round(newY * 10000) / 10000;
    } else {
      let newL = initL;
      let newT = initT;
      let newR = initR;
      let newB = initB;

      if (['w', 'nw', 'sw'].includes(activeDragMode)) {
        newL = Math.max(0.0, Math.min(initR - 0.05, initL + dx));
      }
      if (['e', 'ne', 'se'].includes(activeDragMode)) {
        newR = Math.max(initL + 0.05, Math.min(1.0, initR + dx));
      }
      if (['n', 'nw', 'ne'].includes(activeDragMode)) {
        newT = Math.max(0.0, Math.min(initB - 0.04, initT + dy));
      }
      if (['s', 'sw', 'se'].includes(activeDragMode)) {
        newB = Math.max(initT + 0.04, Math.min(1.0, initB + dy));
      }

      maskObj.x = Math.round(newL * 10000) / 10000;
      maskObj.y = Math.round(newT * 10000) / 10000;
      maskObj.width = Math.round(Math.max(0.05, newR - newL) * 10000) / 10000;
      maskObj.height = Math.round(Math.max(0.04, newB - newT) * 10000) / 10000;
    }
  }

  renderCanvasOverlays();
}

function onPointerUpCanvas(e) {
  if (activeDragMode) {
    activeDragMode = null;
    activeDragTargetId = null;
    window.removeEventListener('pointermove', onPointerMoveCanvas);
    window.removeEventListener('pointerup', onPointerUpCanvas);
    window.removeEventListener('pointercancel', onPointerUpCanvas);
  }
}

function addNewMaskRegion() {
  const maskCount = maskRegions.length + 1;
  const newMask = {
    id: `mask_${Date.now()}`,
    x: 0.10,
    y: Math.max(0.10, Math.min(0.75, 0.70 - (maskCount - 1) * 0.12)),
    width: 0.80,
    height: 0.14,
    type: 'blur', // 'blur' | 'solid'
    blur_strength: 15,
    color: '#000000',
    opacity: 0.85,
    enabled: true,
    locked: false,
  };
  maskRegions.push(newMask);
  selectedObjectId = newMask.id;
  renderMaskRegionsList();
  renderCanvasOverlays();
  showToast(`Đã thêm Vùng che #${maskCount}`);
}

function removeMaskRegion(maskId) {
  maskRegions = maskRegions.filter((m) => m.id !== maskId);
  if (selectedObjectId === maskId) {
    selectedObjectId = 'subtitle';
  }
  renderMaskRegionsList();
  renderCanvasOverlays();
  showToast('Đã xóa vùng che.');
}

function toggleMaskVisibility(maskId) {
  const m = maskRegions.find((item) => item.id === maskId);
  if (m) {
    m.enabled = !m.enabled;
    renderMaskRegionsList();
    renderCanvasOverlays();
  }
}

function toggleMaskLock(maskId) {
  const m = maskRegions.find((item) => item.id === maskId);
  if (m) {
    m.locked = !m.locked;
    renderMaskRegionsList();
    renderCanvasOverlays();
  }
}

function hexToRgba(hex, alpha = 1.0) {
  let c = (hex || '#000000').replace('#', '');
  if (c.length === 3) c = c.split('').map((x) => x + x).join('');
  const num = parseInt(c, 16) || 0;
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function renderMaskRegionsList() {
  if (!maskRegionsList) return;
  const placeholder = document.getElementById('emptyMasksPlaceholder');

  if (maskRegions.length === 0) {
    maskRegionsList.innerHTML = `
      <div id="emptyMasksPlaceholder" style="font-size: 0.72rem; color: var(--text-dim); text-align: center; padding: 0.6rem; border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm);">
        Chưa có vùng che nào. Bấm "+ Thêm vùng che" để tạo.
      </div>
    `;
    return;
  }

  maskRegionsList.innerHTML = maskRegions
    .map((m, idx) => {
      const isActive = selectedObjectId === m.id;
      const activeClass = isActive ? 'is-active' : '';
      const isSolid = m.type === 'solid';

      return `
        <div class="mask-item-card ${activeClass}" data-mask-id="${m.id}">
          <div class="mask-item-header">
            <div class="mask-item-title">
              <span>${isSolid ? '⬛' : '🌫️'}</span>
              <span>Vùng che #${idx + 1}</span>
              ${m.locked ? '<span style="font-size:0.65rem; color:#f59e0b;">🔒</span>' : ''}
              ${!m.enabled ? '<span style="font-size:0.65rem; color:var(--text-dim);">(Ẩn)</span>' : ''}
            </div>
            <div class="mask-item-actions">
              <button type="button" class="btn-mask-icon ${m.enabled ? 'active' : ''}" data-action="toggle-vis" title="${m.enabled ? 'Ẩn vùng che' : 'Hiện vùng che'}">
                ${m.enabled ? '👁' : '🚫'}
              </button>
              <button type="button" class="btn-mask-icon ${m.locked ? 'active' : ''}" data-action="toggle-lock" title="${m.locked ? 'Mở khóa' : 'Khóa vị trí'}">
                ${m.locked ? '🔒' : '🔓'}
              </button>
              <button type="button" class="btn-mask-icon danger" data-action="delete" title="Xóa vùng che">
                🗑
              </button>
            </div>
          </div>

          <!-- Type selection -->
          <div style="display: flex; gap: 0.35rem; align-items: center; margin-top: 0.15rem;">
            <select class="form-select mask-type-select" style="font-size: 0.70rem; padding: 0.2rem 0.4rem; flex: 1;">
              <option value="blur" ${m.type === 'blur' ? 'selected' : ''}>🌫️ Làm mờ (Blur)</option>
              <option value="solid" ${m.type === 'solid' ? 'selected' : ''}>⬛ Màu phủ (Solid)</option>
            </select>
          </div>

          <!-- Type specific controls -->
          ${
            isSolid
              ? `
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.4rem; align-items: center; margin-top: 0.2rem;">
              <input type="color" class="color-input mask-color-input" value="${m.color || '#000000'}" style="width: 24px; height: 24px;">
              <div style="display: flex; flex-direction: column; gap: 0.1rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--text-muted);">
                  <span>Độ phủ</span>
                  <span class="mask-opacity-label">${Math.round((m.opacity || 0.85) * 100)}%</span>
                </div>
                <input type="range" class="range-input mask-opacity-input" min="0" max="1" step="0.05" value="${m.opacity !== undefined ? m.opacity : 0.85}">
              </div>
            </div>
          `
              : `
            <div style="display: flex; flex-direction: column; gap: 0.1rem; margin-top: 0.2rem;">
              <div style="display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--text-muted);">
                <span>Độ mờ (Blur)</span>
                <span class="mask-blur-label">${m.blur_strength || 15}px</span>
              </div>
              <input type="range" class="range-input mask-blur-input" min="2" max="30" step="1" value="${m.blur_strength || 15}">
            </div>
          `
          }
        </div>
      `;
    })
    .join('');

  // Attach card event listeners
  maskRegionsList.querySelectorAll('.mask-item-card').forEach((card) => {
    const maskId = card.dataset.maskId;
    const maskObj = maskRegions.find((m) => m.id === maskId);
    if (!maskObj) return;

    card.addEventListener('click', (e) => {
      if (e.target.closest('button') || e.target.closest('input') || e.target.closest('select')) return;
      selectedObjectId = maskId;
      renderMaskRegionsList();
      renderCanvasOverlays();
    });

    const btnVis = card.querySelector('[data-action="toggle-vis"]');
    if (btnVis) btnVis.addEventListener('click', () => toggleMaskVisibility(maskId));

    const btnLock = card.querySelector('[data-action="toggle-lock"]');
    if (btnLock) btnLock.addEventListener('click', () => toggleMaskLock(maskId));

    const btnDel = card.querySelector('[data-action="delete"]');
    if (btnDel) btnDel.addEventListener('click', () => removeMaskRegion(maskId));

    const typeSelect = card.querySelector('.mask-type-select');
    if (typeSelect) {
      typeSelect.addEventListener('change', (e) => {
        maskObj.type = e.target.value;
        renderMaskRegionsList();
        renderCanvasOverlays();
      });
    }

    const blurInput = card.querySelector('.mask-blur-input');
    if (blurInput) {
      blurInput.addEventListener('input', (e) => {
        maskObj.blur_strength = parseInt(e.target.value) || 15;
        const label = card.querySelector('.mask-blur-label');
        if (label) label.textContent = `${maskObj.blur_strength}px`;
        renderCanvasOverlays();
      });
    }

    const colorInput = card.querySelector('.mask-color-input');
    if (colorInput) {
      colorInput.addEventListener('input', (e) => {
        maskObj.color = e.target.value;
        renderCanvasOverlays();
      });
    }

    const opacityInput = card.querySelector('.mask-opacity-input');
    if (opacityInput) {
      opacityInput.addEventListener('input', (e) => {
        maskObj.opacity = parseFloat(e.target.value) || 0.85;
        const label = card.querySelector('.mask-opacity-label');
        if (label) label.textContent = `${Math.round(maskObj.opacity * 100)}%`;
        renderCanvasOverlays();
      });
    }
  });
}

function renderCanvasOverlays() {
  const isEnabled = optSubtitle ? optSubtitle.checked : true;
  const hasVideoLoaded = Boolean(
    videoPreview &&
    videoPreview.style.display !== 'none' &&
    (videoPreview.src || (currentJobId && dropzone && dropzone.style.display === 'none'))
  );

  // 1. LAYER 1 (z=10): MASK CANVAS OVERLAY
  if (maskCanvasLayer) {
    if (!hasVideoLoaded) {
      maskCanvasLayer.innerHTML = '';
      maskCanvasLayer.style.display = 'none';
    } else {
      maskCanvasLayer.style.display = 'block';
      maskCanvasLayer.innerHTML = maskRegions
        .filter((m) => m.enabled)
        .map((m) => {
          const isSolid = m.type === 'solid';
          const bgStyle = isSolid ? hexToRgba(m.color, m.opacity) : 'rgba(0,0,0,0.18)';
          const blurVal = `${m.blur_strength || 15}px`;

          return `
            <div class="mask-region-box type-${m.type}" style="
              left: ${(m.x * 100).toFixed(2)}%;
              top: ${(m.y * 100).toFixed(2)}%;
              width: ${(m.width * 100).toFixed(2)}%;
              height: ${(m.height * 100).toFixed(2)}%;
              --blur-px: ${blurVal};
              --mask-solid-bg: ${bgStyle};
            "></div>
          `;
        })
        .join('');
    }
  }

  // 2. LAYER 2 (z=20): SUBTITLE LIVE OVERLAY
  if (subtitleLiveOverlay) {
    if (!hasVideoLoaded || !isEnabled) {
      subtitleLiveOverlay.style.display = 'none';
      subtitleLiveOverlay.innerHTML = '';
    } else {
      subtitleLiveOverlay.style.display = 'block';
      const leftPct = ((subtitleLayout.x - subtitleLayout.width / 2) * 100).toFixed(2);
      const topPct = ((subtitleLayout.y - subtitleLayout.height / 2) * 100).toFixed(2);
      const wPct = (subtitleLayout.width * 100).toFixed(2);
      const hPct = (subtitleLayout.height * 100).toFixed(2);

      let curText = 'Đây là phụ đề';
      if (currentSegments && currentSegments.length > 0 && videoPreview && videoPreview.currentTime > 0) {
        const curTime = videoPreview.currentTime;
        const activeSeg = currentSegments.find((s) => curTime >= s.start && curTime <= s.end);
        if (activeSeg) {
          curText = activeSeg.translated_text || activeSeg.text || activeSeg.original_text || '';
        } else {
          curText = '';
        }
      }

      subtitleLiveOverlay.innerHTML = `
        <div class="subtitle-draggable-box" id="subtitleDraggableBox" style="
          left: ${leftPct}%;
          top: ${topPct}%;
          width: ${wPct}%;
          height: ${hPct}%;
        ">
          <span class="subtitle-text-content" id="subtitleTextContent" style="${curText ? '' : 'display:none;'}">${escapeHtml(curText)}</span>
        </div>
      `;

      updateSubtitleOverlayStyles();
    }
  }

  // 3. LAYER 3 (z=30): EDITOR INTERACTION & 8-POINT HANDLES LAYER
  if (editorInteractionLayer) {
    if (!hasVideoLoaded) {
      editorInteractionLayer.innerHTML = '';
      editorInteractionLayer.style.display = 'none';
    } else {
      editorInteractionLayer.style.display = 'block';
      const handlesHtml = `
        <div class="resize-handle handle-nw" data-handle="nw"></div>
        <div class="resize-handle handle-n" data-handle="n"></div>
        <div class="resize-handle handle-ne" data-handle="ne"></div>
        <div class="resize-handle handle-e" data-handle="e"></div>
        <div class="resize-handle handle-se" data-handle="se"></div>
        <div class="resize-handle handle-s" data-handle="s"></div>
        <div class="resize-handle handle-sw" data-handle="sw"></div>
        <div class="resize-handle handle-w" data-handle="w"></div>
      `;

      let boxesHtml = '';

      // Mask Bounding Boxes
      maskRegions.forEach((m) => {
        if (!m.enabled) return;
        const isSel = selectedObjectId === m.id;
        const leftPct = (m.x * 100).toFixed(2);
        const topPct = (m.y * 100).toFixed(2);
        const wPct = (m.width * 100).toFixed(2);
        const hPct = (m.height * 100).toFixed(2);

        boxesHtml += `
          <div class="editor-bounding-box mask-box ${isSel ? 'is-selected' : ''} ${m.locked ? 'is-locked' : ''}" data-object-id="${m.id}" style="
            left: ${leftPct}%;
            top: ${topPct}%;
            width: ${wPct}%;
            height: ${hPct}%;
          ">
            ${isSel && !m.locked ? handlesHtml : ''}
          </div>
        `;
      });

      // Subtitle Bounding Box
      if (isEnabled) {
        const isSel = selectedObjectId === 'subtitle';
        const leftPct = ((subtitleLayout.x - subtitleLayout.width / 2) * 100).toFixed(2);
        const topPct = ((subtitleLayout.y - subtitleLayout.height / 2) * 100).toFixed(2);
        const wPct = (subtitleLayout.width * 100).toFixed(2);
        const hPct = (subtitleLayout.height * 100).toFixed(2);

        boxesHtml += `
          <div class="editor-bounding-box ${isSel ? 'is-selected' : ''}" data-object-id="subtitle" style="
            left: ${leftPct}%;
            top: ${topPct}%;
            width: ${wPct}%;
            height: ${hPct}%;
          ">
            ${isSel ? handlesHtml : ''}
          </div>
        `;
      }

      editorInteractionLayer.innerHTML = boxesHtml;
    }
  }
}

function updateSubtitleVisibilityAndPreview() {
  const isEnabled = optSubtitle ? optSubtitle.checked : true;
  if (subtitleStyleCard) {
    subtitleStyleCard.style.opacity = isEnabled ? '1' : '0.4';
    subtitleStyleCard.style.pointerEvents = isEnabled ? 'auto' : 'none';
  }
  if (subModeSubOption) {
    subModeSubOption.style.opacity = isEnabled ? '1' : '0.4';
    subModeSubOption.style.pointerEvents = isEnabled ? 'auto' : 'none';
  }
  renderCanvasOverlays();
}

function updateSubtitleOverlayStyles() {
  const textContent = document.getElementById('subtitleTextContent');
  if (!textContent) return;

  const font = subFontFamily ? subFontFamily.value || 'Arial' : 'Arial';
  const size = subFontSize ? parseInt(subFontSize.value) || 36 : 36;
  const color = subTextColor ? subTextColor.value || '#ffffff' : '#ffffff';
  const outlineColor = subOutlineColor ? subOutlineColor.value || '#000000' : '#000000';
  const strokeW = subOutlineWidth ? parseFloat(subOutlineWidth.value) || 2.5 : 2.5;
  const bold = subBoldCheckbox ? subBoldCheckbox.checked : true;
  const shadow = subShadowCheckbox ? subShadowCheckbox.checked : true;

  // Responsive scale factor based on video player wrapper width
  const frameW = videoFrameWrapper ? videoFrameWrapper.clientWidth || 640 : 640;
  const scale = Math.max(0.4, Math.min(1.0, frameW / 1000));
  const effectiveSize = Math.round(size * scale);

  textContent.style.fontFamily = `"${font}", sans-serif`;
  textContent.style.fontSize = `${effectiveSize}px`;
  textContent.style.fontWeight = bold ? '700' : '400';
  textContent.style.color = color;

  if (strokeW > 0) {
    const scaledStroke = Math.max(1, (strokeW * scale).toFixed(1));
    textContent.style.webkitTextStroke = `${scaledStroke}px ${outlineColor}`;
    textContent.style.paintOrder = 'stroke fill';
  } else {
    textContent.style.webkitTextStroke = 'none';
  }

  if (shadow) {
    textContent.style.textShadow = '0 2px 8px rgba(0,0,0,0.85), 0 0 3px #000';
  } else {
    textContent.style.textShadow = 'none';
  }
}

function updateSubtitleOverlayText() {
  renderCanvasOverlays();
}

function getSubtitleStyleConfig() {
  return {
    font_family: subFontFamily ? subFontFamily.value || 'Arial' : 'Arial',
    font_size: subFontSize ? parseInt(subFontSize.value) || 36 : 36,
    primary_color: subTextColor ? subTextColor.value || '#FFFFFF' : '#FFFFFF',
    outline_color: subOutlineColor ? subOutlineColor.value || '#000000' : '#000000',
    outline_width: subOutlineWidth ? parseFloat(subOutlineWidth.value) || 2.5 : 2.5,
    position_x: subtitleLayout.x,
    position_y: subtitleLayout.y,
    width: subtitleLayout.width,
    height: subtitleLayout.height,
    bold: subBoldCheckbox ? subBoldCheckbox.checked : true,
    shadow: subShadowCheckbox ? (subShadowCheckbox.checked ? 1.0 : 0.0) : 1.0,
  };
}

function getMaskRegionsConfig() {
  return maskRegions.map((m) => ({
    id: m.id,
    x: m.x,
    y: m.y,
    width: m.width,
    height: m.height,
    type: m.type || 'blur',
    blur_strength: m.blur_strength || 15,
    color: m.color || '#000000',
    opacity: m.opacity !== undefined ? m.opacity : 0.85,
    enabled: m.enabled !== false,
    locked: Boolean(m.locked),
  }));
}

// ================= FILE UPLOAD & BATCH MANAGEMENT (NO AUTO-RUN) =================
async function handleFilesSelected(files) {
  if (!files || files.length === 0) return;
  const selectedFiles = Array.from(files);

  console.log('[UPLOAD] Bắt đầu tải lên:', selectedFiles.length, 'file');

  // 1. Luôn Reset sạch workspace trước khi thực hiện upload file mới (Unified cleanup)
  resetWorkspaceToNoJob();
  const uploadGen = ++workspaceGeneration;

  // Validate số lượng file (1 đến 5 video)
  if (selectedFiles.length > 5) {
    showToast('Tối đa 5 video cho mỗi lượt xử lý (TEST 5)', 'error');
    return;
  }

  // Validate định dạng
  for (const f of selectedFiles) {
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      showToast(`File "${f.name}" không hợp lệ. Chỉ chấp nhận MP4, MOV, MKV, WEBM.`, 'error');
      return;
    }
  }

  // Hiển thị upload progress
  progressBox.style.display = 'block';
  progressStatus.textContent = selectedFiles.length > 1 ? `Đang tải lên ${selectedFiles.length} video...` : 'Đang tải video lên máy chủ...';
  progressBarFill.style.width = '10%';
  progressPercent.textContent = '10%';
  dropzone.style.display = 'none';

  try {
    if (selectedFiles.length === 1) {
      // 1 Video Upload (100% Tương thích ngược)
      const res = await apiClient.uploadVideo(selectedFiles[0], (pct) => {
        if (workspaceGeneration !== uploadGen) return;
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
      });

      if (workspaceGeneration !== uploadGen) {
        console.warn('[UPLOAD] Bỏ qua kết quả upload do workspace đã đổi');
        return;
      }

      workspaceMode = 'job';
      currentJob = res;
      currentJobId = res.job_id;
      currentBatchId = null;
      batchJobs = [res];
      activeJobIndex = 0;
      currentSegments = [];
      translatedSegments = [];
      subtitleData = [];
      pipelineState = res.stages || { upload: { status: 'completed' }, metadata: { status: 'completed' } };

      localStorage.setItem('workspace_mode', 'job');
      localStorage.setItem('last_job_id', currentJobId);
      localStorage.removeItem('last_batch_id');

      batchQueueBar.style.display = 'none';
      bindVideoToPreview(selectedFiles[0], res.video);

      // Đưa giao diện về trạng thái UPLOADED / READY (TUYỆT ĐỐI KHÔNG TỰ CHẠY PIPELINE)
      renderUploadedReadyState(res);
      showToast('Tải lên video thành công. Hãy chọn cấu hình và nhấn BẮT ĐẦU XỬ LÝ.');
    } else {
      // Batch Upload 2-5 Videos (Phase 3)
      const res = await apiClient.uploadBatchVideos(selectedFiles, (pct) => {
        if (workspaceGeneration !== uploadGen) return;
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
      });

      if (workspaceGeneration !== uploadGen) {
        console.warn('[UPLOAD] Bỏ qua kết quả upload do workspace đã đổi');
        return;
      }

      workspaceMode = 'batch';
      currentBatchId = res.batch_id;
      batchJobs = res.jobs;
      activeJobIndex = 0;
      currentJob = batchJobs[0];
      currentJobId = batchJobs[0].job_id;
      currentSegments = [];
      translatedSegments = [];
      subtitleData = [];
      pipelineState = batchJobs[0].stages || { upload: { status: 'completed' }, metadata: { status: 'completed' } };

      localStorage.setItem('workspace_mode', 'batch');
      localStorage.setItem('last_batch_id', currentBatchId);
      localStorage.setItem('last_job_id', currentJobId);

      renderBatchQueueBar();
      bindVideoToPreview(selectedFiles[0], batchJobs[0].video);

      // Đưa giao diện về trạng thái UPLOADED / READY
      renderUploadedReadyState(batchJobs[0]);
      showToast(`Đã tải lên ${batchJobs.length} video vào hàng đợi. Sẵn sàng xử lý.`);
    }
  } catch (err) {
    console.error('[UPLOAD_FATAL]', err);
    showToast(err.message || 'Lỗi khi tải lên file', 'error');
    resetWorkspaceToNoJob();
  }
}

/**
 * Hiển thị chính xác trạng thái UPLOADED / READY sau khi tải lên thành công:
 * - Progress = 0% / Ẩn
 * - START Button = Enabled
 * - Log = Chỉ ghi Upload + Metadata
 * - Stepper = Step 1 completed, Step 2-6 pending
 * - Live Subtitle Preview = Bật câu mẫu
 */
function renderUploadedReadyState(job) {
  isProcessing = false;
  stopPolling();

  // 1. Progress Bar ẩn hoặc 0%
  progressBox.style.display = 'none';
  progressBarFill.style.width = '0%';
  progressPercent.textContent = '0%';

  // 2. Kích hoạt nút START
  runPipelineBtn.disabled = false;
  runPipelineBtn.classList.remove('btn-disabled');
  runPipelineBtn.innerHTML = '<span>🚀</span> BẮT ĐẦU XỬ LÝ';

  // 3. Ẩn Retry Banner
  retryActionBox.style.display = 'none';

  // 4. Steppers & Pipeline Pills
  const stages = job.stages || {
    upload: { status: 'completed' },
    metadata: { status: 'completed' }
  };
  renderPipelinePills(stages);
  renderStepperItems(stages);

  // 5. Nhật ký xử lý: Chỉ hiển thị Upload & Metadata
  renderProcessingLogs(stages);

  // 6. Subtitles: Trạng thái chờ
  renderSubtitles();

  // 7. Final Video: Chờ xử lý
  renderFinalVideoOutput(job);

  // 8. Cập nhật Live Overlay & Masks
  renderMaskRegionsList();
  updateSubtitleVisibilityAndPreview();
}

let currentPreviewObjectUrl = null;

function bindVideoToPreview(fileOrUrl, videoMeta) {
  if (currentPreviewObjectUrl) {
    try {
      URL.revokeObjectURL(currentPreviewObjectUrl);
    } catch (e) {}
    currentPreviewObjectUrl = null;
  }

  if (typeof fileOrUrl === 'string') {
    videoPreview.src = fileOrUrl;
  } else if (fileOrUrl instanceof File) {
    currentPreviewObjectUrl = URL.createObjectURL(fileOrUrl);
    videoPreview.src = currentPreviewObjectUrl;
  } else if (videoMeta && videoMeta.preview_url) {
    videoPreview.src = videoMeta.preview_url;
  }

  videoPreview.style.display = 'block';
  dropzone.style.display = 'none';

  if (videoMeta) {
    videoBadgeName.textContent = `🎬 ${videoMeta.filename || 'Video'}`;
    videoBadgeRes.textContent = `🔲 ${videoMeta.resolution || '—'}`;
    videoBadgeDuration.textContent = `⏱ ${videoMeta.duration_formatted || '—'}`;
    videoBadgeFps.textContent = `🎬 ${videoMeta.fps || 30}fps`;

    videoName.textContent = videoMeta.filename || '—';
    videoFormat.textContent = (videoMeta.filename || '').split('.').pop().toUpperCase() || 'MP4';
    videoDuration.textContent = videoMeta.duration_formatted || '—';
    videoFps.textContent = `${videoMeta.fps || 30} fps`;
    videoResolution.textContent = videoMeta.resolution || '—';
    videoRatio.textContent = videoMeta.ratio || '16:9';
    videoSize.textContent = videoMeta.size || '—';
    videoUploadDate.textContent = new Date().toLocaleDateString('vi-VN');
  }
}

function renderBatchQueueBar() {
  if (!currentBatchId || batchJobs.length <= 1) {
    batchQueueBar.style.display = 'none';
    return;
  }

  batchQueueBar.style.display = 'flex';
  queueCountBadge.textContent = `${batchJobs.length}/5 video`;

  queuePillsList.innerHTML = batchJobs
    .map((j, idx) => {
      const activeClass = idx === activeJobIndex ? 'active' : '';
      const v = j.video || j.video_info || {};
      const name = v.filename || `Video #${idx + 1}`;
      const status = j.status || 'uploaded';
      let statusLabel = 'Chờ';
      let badgeClass = 'queued';

      if (status === 'processing') {
        statusLabel = 'Đang xử lý';
        badgeClass = 'processing';
      } else if (status === 'completed') {
        statusLabel = 'Xong ✓';
        badgeClass = 'completed';
      } else if (status === 'failed') {
        statusLabel = 'Lỗi ✕';
        badgeClass = 'failed';
      }

      return `
        <div class="queue-pill-item ${activeClass}" data-index="${idx}" data-job-id="${j.job_id}">
          <span>🎬 ${escapeHtml(name)}</span>
          <span class="queue-status-badge ${badgeClass}">${statusLabel}</span>
        </div>
      `;
    })
    .join('');

  queuePillsList.querySelectorAll('.queue-pill-item').forEach((item) => {
    item.addEventListener('click', () => {
      const idx = parseInt(item.dataset.index);
      switchBatchActiveJob(idx);
    });
  });
}

function switchBatchActiveJob(index) {
  if (index < 0 || index >= batchJobs.length) return;
  activeJobIndex = index;
  const job = batchJobs[index];
  currentJobId = job.job_id;
  localStorage.setItem('last_job_id', currentJobId);

  renderBatchQueueBar();
  apiClient.getJob(currentJobId).then((fullJob) => {
    batchJobs[index] = fullJob;
    renderJobState(fullJob);
    if (fullJob.video) {
      bindVideoToPreview(fullJob.video.preview_url || `/api/jobs/${currentJobId}/video`, fullJob.video);
    }
  });
}

// ================= PIPELINE ORCHESTRATION & EXECUTION =================
async function handleRunPipeline() {
  if (!currentJobId && !currentBatchId) {
    showToast('Vui lòng tải video lên trước khi xử lý.', 'error');
    return;
  }

  // Nếu job hiện tại đang ở trạng thái failed, chuyển hướng sang handleRetry(true) để áp dụng RetryPlan
  if (currentJob && currentJob.status === 'failed') {
    return handleRetry(true);
  }

  isProcessing = true;
  runPipelineBtn.disabled = true;
  runPipelineBtn.classList.add('btn-disabled');
  runPipelineBtn.innerHTML = '<span>⏳</span> Đang xử lý...';
  retryActionBox.style.display = 'none';

  const isSubEnabled = optSubtitle.checked;
  const subMode = subModeSelect.value || 'burn';

  const config = {
    run_stt: optSTT.checked,
    whisper_model: whisperModelSelect.value || 'small',
    run_translation: optTranslate.checked,
    run_tts: optTTS.checked,
    create_subtitle: isSubEnabled,
    subtitle_enabled: isSubEnabled,
    subtitle_mode: subMode,
    burn_subtitles: isSubEnabled && subMode === 'burn',
    render_video: optRender.checked,
    source_language: sourceLangSelect.value,
    target_language: targetLangSelect.value,
    translation_style: translationStyleSelect.value,
    voice_id: voiceSelect.value,
    speed_rate: speedRateValue.textContent,
    pitch: pitchValue.textContent,
    voice_volume: parseInt(voiceVolumeRange.value) / 100.0,
    background_volume: parseInt(bgVolumeRange.value) / 100.0,
    keep_background_audio: keepBgAudioCheckbox.checked,
    output_resolution: resolutionSelect.value,
    output_format: formatSelect.value,
    api_key: geminiApiKeyInput.value.trim() || null,
    subtitle_style: getSubtitleStyleConfig(),
    mask_regions: getMaskRegionsConfig(),
  };

  try {
    if (currentBatchId && batchJobs.length > 1) {
      // Chạy Batch tuần tự (concurrency = 1)
      const res = await apiClient.processBatch(currentBatchId, config);
      showToast(`Đã bắt đầu xử lý tuần tự ${batchJobs.length} video.`);
      startBatchPolling(currentBatchId);
    } else {
      // Chạy 1 Job đơn lẻ
      const res = await apiClient.processPipeline(currentJobId, config);
      if (currentJob) {
        currentJob.status = 'processing';
        if (res.stages) currentJob.stages = res.stages;
        if (currentJob.artifacts && currentJob.artifacts.final_video) {
          currentJob.artifacts.final_video.current = false;
          currentJob.artifacts.final_video.reprocessing = true;
        }
        renderJobState(currentJob);
      }
      showToast('Đã bắt đầu tiến trình xử lý video.');
      startJobPolling(currentJobId);
    }
  } catch (err) {
    showToast(err.message || 'Lỗi khi khởi chạy pipeline', 'error');
    isProcessing = false;
    runPipelineBtn.disabled = false;
    runPipelineBtn.classList.remove('btn-disabled');
    runPipelineBtn.innerHTML = '<span>🚀</span> BẮT ĐẦU XỬ LÝ';
  }
}

// ================= RETRY / RESUME LOGIC (Phase 1 / TEST 1, TEST 10) =================
async function handleRetry(resumeFromFailed = true) {
  if (!currentJobId) return;

  btnRetryFailed.disabled = true;
  btnRerunAll.disabled = true;
  btnRetryFailed.innerHTML = '<span>⏳</span> Đang khởi động lại...';
  btnRerunAll.innerHTML = '<span>⏳</span> Đang khởi động lại...';

  isProcessing = true;
  runPipelineBtn.disabled = true;
  runPipelineBtn.classList.add('btn-disabled');
  runPipelineBtn.innerHTML = '<span>⏳</span> Đang xử lý...';

  const isSubEnabled = optSubtitle.checked;
  const subMode = subModeSelect.value || 'burn';

  const config = {
    run_stt: optSTT.checked,
    whisper_model: whisperModelSelect.value || 'small',
    run_translation: optTranslate.checked,
    run_tts: optTTS.checked,
    create_subtitle: isSubEnabled,
    subtitle_enabled: isSubEnabled,
    subtitle_mode: subMode,
    burn_subtitles: isSubEnabled && subMode === 'burn',
    render_video: optRender.checked,
    source_language: sourceLangSelect.value,
    target_language: targetLangSelect.value,
    translation_style: translationStyleSelect.value,
    voice_id: voiceSelect.value,
    speed_rate: speedRateValue.textContent,
    pitch: pitchValue.textContent,
    voice_volume: parseInt(voiceVolumeRange.value) / 100.0,
    background_volume: parseInt(bgVolumeRange.value) / 100.0,
    keep_background_audio: keepBgAudioCheckbox.checked,
    output_resolution: resolutionSelect.value,
    output_format: formatSelect.value,
    api_key: geminiApiKeyInput.value.trim() || null,
    subtitle_style: getSubtitleStyleConfig(),
    mask_regions: getMaskRegionsConfig(),
  };

  try {
    const res = await apiClient.retryJob(currentJobId, {
      resume_from_failed: resumeFromFailed,
      pipeline_config: config,
    });
    retryActionBox.style.display = 'none';
    if (res.stages) {
      if (currentJob) {
        currentJob.stages = res.stages;
        currentJob.status = res.status || 'processing';
        currentJob.progress = res.progress !== undefined ? res.progress : currentJob.progress;
      }
      renderPipelinePills(res.stages);
      renderStepperItems(res.stages);
    }
    progressBox.style.display = 'block';
    progressStatus.textContent = res.message || 'Đang tiếp tục xử lý...';
    showToast(resumeFromFailed ? 'Đang thử lại từ đoạn bị lỗi...' : 'Đang chạy lại toàn bộ pipeline...');
    startJobPolling(currentJobId);
  } catch (err) {
    showToast(err.message || 'Lỗi khi thử lại Job', 'error');
    isProcessing = false;
    btnRetryFailed.disabled = false;
    btnRerunAll.disabled = false;
    btnRetryFailed.innerHTML = '<span>🔄</span> Thử lại từ đoạn lỗi';
    btnRerunAll.innerHTML = '<span>⏮</span> Chạy lại từ đầu';
    runPipelineBtn.disabled = false;
    runPipelineBtn.classList.remove('btn-disabled');
    runPipelineBtn.innerHTML = '<span>🔄</span> THỬ LẠI XỬ LÝ';
  }
}

// ================= POLLING & REAL-TIME STATE SYNC =================
function startJobPolling(jobId) {
  stopPolling();
  activePollJobId = jobId;
  const pollGeneration = workspaceGeneration;

  activePollTimer = setInterval(async () => {
    try {
      // Race Condition & Generation Token Protection (TEST 11, 12, 19, 29, 31)
      if (activePollJobId !== jobId || currentJobId !== jobId || workspaceGeneration !== pollGeneration) {
        stopPolling();
        return;
      }

      const job = await apiClient.getJob(jobId);

      // Kiểm tra lại sau khi await để tránh state overwrite nếu người dùng đã chuyển job/reset
      if (activePollJobId !== jobId || currentJobId !== jobId || workspaceGeneration !== pollGeneration) {
        return;
      }

      renderJobState(job);

      if (job.status === 'completed' || job.status === 'failed') {
        stopPolling();
        isProcessing = false;
        runPipelineBtn.disabled = false;
        runPipelineBtn.classList.remove('btn-disabled');
        runPipelineBtn.innerHTML = job.status === 'failed' ? '<span>🔄</span> THỬ LẠI XỬ LÝ' : '<span>🚀</span> BẮT ĐẦU XỬ LÝ';

        if (job.status === 'completed') {
          showToast('Xử lý video hoàn tất thành công!');
        } else {
          showToast(`Tác vụ thất bại: ${job.error || 'Đã xảy ra lỗi'}`, 'error');
        }
      }
    } catch (e) {
      console.warn('Lỗi polling job:', e);
    }
  }, 1000);
}

function startBatchPolling(batchId) {
  if (activeBatchPollTimer) clearInterval(activeBatchPollTimer);
  const batchPollGeneration = workspaceGeneration;

  activeBatchPollTimer = setInterval(async () => {
    try {
      if (currentBatchId !== batchId || workspaceGeneration !== batchPollGeneration) {
        clearInterval(activeBatchPollTimer);
        activeBatchPollTimer = null;
        return;
      }

      const batch = await apiClient.getBatch(batchId);
      if (currentBatchId !== batchId || workspaceGeneration !== batchPollGeneration) return;

      if (batch.jobs_detail) {
        batchJobs = batch.jobs_detail;
        renderBatchQueueBar();
        renderBatchResults(batch);

        if (batch.current_job_id) {
          const curIndex = batchJobs.findIndex((j) => j.job_id === batch.current_job_id);
          if (curIndex !== -1 && curIndex !== activeJobIndex) {
            activeJobIndex = curIndex;
            currentJobId = batch.current_job_id;
            renderJobState(batchJobs[curIndex]);
          } else if (curIndex !== -1) {
            renderJobState(batchJobs[curIndex]);
          }
        }
      }

      if (batch.status === 'completed' || batch.status === 'completed_with_errors') {
        clearInterval(activeBatchPollTimer);
        activeBatchPollTimer = null;
        isProcessing = false;
        runPipelineBtn.disabled = false;
        runPipelineBtn.classList.remove('btn-disabled');
        runPipelineBtn.innerHTML = '<span>🚀</span> BẮT ĐẦU XỬ LÝ';

        if (batch.status === 'completed') {
          showToast('Toàn bộ hàng đợi batch đã hoàn thành xuất sắc!');
        } else {
          showToast('Hàng đợi batch đã hoàn tất với một số video bị lỗi (Error Isolation).', 'warning');
        }
      }
    } catch (e) {
      console.warn('Lỗi polling batch:', e);
    }
  }, 1200);
}

function stopPolling() {
  if (activePollTimer) {
    clearInterval(activePollTimer);
    activePollTimer = null;
  }
  activePollJobId = null;
}

// ================= RENDER JOB STATE =================
function renderJobState(job) {
  if (!job) return;

  // Strict NO_JOB and Stale Payload Guard (Section 3 & 4)
  if (!canApplyJobPayload(job.job_id)) {
    return;
  }

  currentJob = job;
  currentJobId = job.job_id;
  pipelineState = job.stages || {};
  progressState = job.progress || 0;
  errorState = job.error || null;
  jobArtifacts = job.artifacts || null;
  if (job.segments) {
    currentSegments = job.segments;
    translatedSegments = job.segments.filter((s) => s.translated_text);
    subtitleData = job.segments;
  }

  const stages = job.stages || {};
  const progress = Math.min(100, Math.max(0, job.progress || 0));
  const isFailed = job.status === 'failed';
  const isCompleted = job.status === 'completed';
  const isUploadedOnly = job.status === 'uploaded' || (!isCompleted && !isFailed && job.status !== 'processing');

  if (isUploadedOnly) {
    renderUploadedReadyState(job);
    return;
  }

  // 1. Progress Bar
  progressBox.style.display = 'block';
  progressBarFill.style.width = `${progress}%`;
  progressPercent.textContent = `${Math.round(progress)}%`;

  if (isCompleted) {
    progressStatus.textContent = 'Hoàn tất toàn bộ tiến trình!';
    progressBarFill.style.background = 'linear-gradient(90deg, #10b981 0%, #059669 100%)';
  } else if (isFailed) {
    progressStatus.textContent = `Thất bại: ${job.error || 'Lỗi xử lý'}`;
    progressBarFill.style.background = '#ef4444';
  } else {
    const activeStageKey = Object.keys(stages).find((k) => stages[k] && stages[k].status === 'running');
    const activeStage = activeStageKey ? stages[activeStageKey] : null;
    const stageMsg = activeStage && activeStage.message ? activeStage.message : 'Đang thực thi pipeline...';
    progressStatus.textContent = stageMsg;
    progressBarFill.style.background = 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)';
  }

  // 2. Retry Box (Phase 1)
  if (isFailed) {
    retryActionBox.style.display = 'block';
    btnRetryFailed.disabled = false;
    btnRerunAll.disabled = false;
    btnRetryFailed.innerHTML = '<span>🔄</span> Thử lại từ đoạn lỗi';
    btnRerunAll.innerHTML = '<span>⏮</span> Chạy lại từ đầu';

    const errText = job.error || '';
    if (errText.includes('API_KEY_INVALID') || errText.includes('Khóa Gemini API')) {
      retryErrorMessage.innerHTML = `🔑 <strong>Gemini API Key không hợp lệ:</strong> Vui lòng bấm "Thay đổi" tại mục Cấu hình dịch thuật để nhập API Key mới, sau đó bấm <strong>Thử lại từ đoạn lỗi</strong>.`;
    } else if (errText.includes('TASK_INTERRUPTED_SERVER_RESTART') || errText.includes('máy chủ khởi động lại')) {
      retryErrorMessage.innerHTML = `🔄 <strong>Máy chủ đã khởi động lại:</strong> Toàn bộ đoạn audio đã tổng hợp được bảo toàn 100%. Bấm <strong>Thử lại từ đoạn lỗi</strong> để tiếp tục ngay.`;
    } else if (errText.includes('AUDIO_SYNC_MISSING_TTS_ARTIFACT') || errText.includes('AUDIO_SYNC_INVALID_SEGMENT_SCHEMA') || errText.includes('AUDIO_SYNC_INVALID_RESULT')) {
      retryErrorMessage.innerHTML = `⚠️ <strong>Lỗi đồng bộ âm thanh:</strong> ${escapeHtml(errText)}. Bấm <strong>Thử lại từ đoạn lỗi</strong> để tự động tái tạo và đồng bộ lại.`;
    } else {
      retryErrorMessage.textContent = `Tác vụ bị lỗi: ${errText || 'Chi tiết trong nhật ký'}`;
    }
  } else {
    retryActionBox.style.display = 'none';
  }

  // 3. Header Pipeline Pills & Steppers
  renderPipelinePills(stages);
  renderStepperItems(stages);

  // 4. Processing Logs
  renderProcessingLogs(stages);

  // 5. Subtitles & Segments
  renderSubtitles();

  // 6. Final Video Output Card
  renderFinalVideoOutput(job);

  // 7. Khôi phục subtitle style & mask regions từ config_snapshot nếu có
  if (job.config_snapshot) {
    const cfg = job.config_snapshot;
    if (cfg.subtitle_style) {
      const s = cfg.subtitle_style;
      if (s.font_family && subFontFamily) subFontFamily.value = s.font_family;
      if (s.font_size && subFontSize) subFontSize.value = s.font_size;
      if (s.primary_color && subTextColor) {
        subTextColor.value = s.primary_color;
        if (subTextColorLabel) subTextColorLabel.textContent = s.primary_color.toUpperCase();
      }
      if (s.outline_color && subOutlineColor) {
        subOutlineColor.value = s.outline_color;
        if (subOutlineColorLabel) subOutlineColorLabel.textContent = s.outline_color.toUpperCase();
      }
      if (s.outline_width !== undefined && subOutlineWidth) {
        subOutlineWidth.value = s.outline_width;
        if (subOutlineWidthValue) subOutlineWidthValue.textContent = `${s.outline_width}px`;
      }
      if (s.bold !== undefined && subBoldCheckbox) subBoldCheckbox.checked = Boolean(s.bold);
      if (s.shadow !== undefined && subShadowCheckbox) subShadowCheckbox.checked = Boolean(s.shadow);
      if (s.position_x !== undefined && s.position_y !== undefined) {
        subtitleLayout.x = parseFloat(s.position_x);
        subtitleLayout.y = parseFloat(s.position_y);
        subtitlePosition.x = subtitleLayout.x;
        subtitlePosition.y = subtitleLayout.y;
      }
      if (s.width !== undefined) subtitleLayout.width = parseFloat(s.width);
      if (s.height !== undefined) subtitleLayout.height = parseFloat(s.height);
    }
    if (Array.isArray(cfg.mask_regions)) {
      maskRegions = cfg.mask_regions.map((m) => ({
        id: m.id || `mask_${Math.random()}`,
        x: parseFloat(m.x !== undefined ? m.x : 0.10),
        y: parseFloat(m.y !== undefined ? m.y : 0.75),
        width: parseFloat(m.width !== undefined ? m.width : 0.80),
        height: parseFloat(m.height !== undefined ? m.height : 0.15),
        type: m.type || 'blur',
        blur_strength: m.blur_strength || 15,
        color: m.color || '#000000',
        opacity: m.opacity !== undefined ? m.opacity : 0.85,
        enabled: m.enabled !== false,
        locked: Boolean(m.locked),
      }));
    }
  }

  // 8. Live Subtitle Overlay & Mask Preview
  renderMaskRegionsList();
  updateSubtitleVisibilityAndPreview();

  // 9. Start Button State
  if (job.status === 'processing') {
    runPipelineBtn.disabled = true;
    runPipelineBtn.classList.add('btn-disabled');
    runPipelineBtn.innerHTML = '<span>⏳</span> Đang xử lý...';
  } else {
    runPipelineBtn.disabled = false;
    runPipelineBtn.classList.remove('btn-disabled');
    runPipelineBtn.innerHTML = isFailed ? '<span>🔄</span> THỬ LẠI XỬ LÝ' : '<span>🚀</span> BẮT ĐẦU XỬ LÝ';
  }
}

function renderPipelinePills(stages) {
  const mapping = [
    { el: stepUpload, name: 'upload' },
    { el: stepExtract, name: 'extract_audio' },
    { el: stepWhisper, name: 'stt' },
    { el: stepTranslate, name: 'translation' },
    { el: stepTTS, name: 'tts' },
    { el: stepRender, name: 'render' },
  ];

  mapping.forEach(({ el, name }) => {
    if (!el) return;
    const st = stages[name] || {};
    const iconSpan = el.querySelector('.icon-check');

    el.classList.remove('active', 'completed', 'failed');
    if (st.status === 'completed') {
      el.classList.add('completed');
      if (iconSpan) iconSpan.textContent = '✓';
    } else if (st.status === 'running') {
      el.classList.add('active');
      if (iconSpan) iconSpan.textContent = '⏳';
    } else if (st.status === 'failed') {
      el.classList.add('failed');
      if (iconSpan) iconSpan.textContent = '✕';
    } else {
      if (iconSpan) iconSpan.textContent = '○';
    }
  });
}

function renderStepperItems(stages) {
  const mapping = [
    { item: stepperItem1, check: stepperCheck1, name: 'extract_audio' },
    { item: stepperItem2, check: stepperCheck2, name: 'stt' },
    { item: stepperItem3, check: stepperCheck3, name: 'translation' },
    { item: stepperItem4, check: stepperCheck4, name: 'tts' },
    { item: stepperItem5, check: stepperCheck5, name: 'audio_sync' },
    { item: stepperItem6, check: stepperCheck6, name: 'render' },
  ];

  mapping.forEach(({ item, check, name }) => {
    if (!item || !check) return;
    const st = stages[name] || {};

    item.classList.remove('active', 'completed', 'failed');
    if (st.status === 'completed') {
      item.classList.add('completed');
      check.textContent = '✓';
      check.style.color = 'var(--emerald-400)';
    } else if (st.status === 'running') {
      item.classList.add('active');
      check.textContent = '⏳';
      check.style.color = '#38bdf8';
    } else if (st.status === 'failed') {
      item.classList.add('failed');
      check.textContent = '✕';
      check.style.color = '#ef4444';
    } else {
      check.textContent = '○';
      check.style.color = 'var(--text-dim)';
    }
  });
}

function renderProcessingLogs(stages) {
  const executedStages = STAGE_ORDER.filter((name) => {
    const s = stages[name];
    return s && (s.status === 'completed' || s.status === 'running' || s.status === 'failed');
  });

  if (executedStages.length === 0) {
    logTableBody.innerHTML = `
      <tr>
        <td colspan="3" style="text-align: center; color: var(--text-dim); padding: 1.5rem 0.5rem; font-size: 0.74rem;">
          Chưa có tác vụ xử lý. Hãy tải video lên để bắt đầu.
        </td>
      </tr>
    `;
    return;
  }

  logTableBody.innerHTML = executedStages
    .map((name) => {
      const st = stages[name] || {};
      const cfg = STAGE_CONFIG[name] || { label: name, icon: '•' };

      let statusBadge = `<span class="badge-status-completed">✓ Hoàn tất</span>`;
      if (st.status === 'running') {
        if (st.is_retrying && st.automatic_attempt) {
          statusBadge = `<span class="badge-status-running" style="color: #fbbf24; border-color: rgba(251, 191, 36, 0.3);">🔄 Tự thử lại (${st.automatic_attempt}/${st.max_automatic_attempts || 3})</span>`;
        } else {
          const hasPct = st.progress !== null && st.progress !== undefined && !isNaN(st.progress);
          const pct = hasPct ? ` (${Math.round(st.progress)}%)` : '';
          statusBadge = `<span class="badge-status-running">⏳ Đang xử lý${pct}</span>`;
        }
      } else if (st.status === 'failed') {
        statusBadge = `<span class="badge-status-failed">✕ Thất bại</span>`;
      }

      const timeStr = formatTime(st.started_at);
      let durStr = '--:--:--';
      if (st.status === 'running') {
        if (st.started_at) {
          const elapsedMs = Math.max(0, Date.now() - new Date(st.started_at).getTime());
          durStr = formatDurationMs(elapsedMs);
        } else {
          durStr = '00:00:00';
        }
      } else if (st.duration_ms !== null && st.duration_ms !== undefined) {
        durStr = formatDurationMs(st.duration_ms);
      }
      const msgStr = st.message || cfg.label;

      return `
        <tr>
          <td style="width: 25%; font-family: monospace; color: var(--text-dim);">
            ${timeStr} <span style="font-size: 0.65rem; color: #475569;">(${durStr})</span>
          </td>
          <td style="width: 50%;">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.76rem;">${cfg.icon} ${escapeHtml(cfg.label)}</div>
            <div style="font-size: 0.68rem; color: var(--text-dim); margin-top: 2px;">${escapeHtml(msgStr)}</div>
          </td>
          <td style="width: 25%; text-align: right;">
            ${statusBadge}
          </td>
        </tr>
      `;
    })
    .join('');
}

function renderSubtitles() {
  if (!currentSegments || currentSegments.length === 0) {
    transcriptList.innerHTML = `
      <div class="empty-state-box" id="subEmptyState">
        <div class="empty-icon">📝</div>
        <div class="empty-title">Chưa có phụ đề</div>
        <div class="empty-desc">Phụ đề sẽ xuất hiện sau khi hoàn thành Whisper STT và Dịch thuật AI.</div>
      </div>
    `;
    totalSubsCount.textContent = '0';
    avgCpsCount.textContent = '—';
    maxCpsCount.textContent = '—';
    downloadOriginalSrtBtn.disabled = true;
    downloadOriginalSrtBtn.classList.add('btn-disabled');
    downloadTranslatedSrtBtn.disabled = true;
    downloadTranslatedSrtBtn.classList.add('btn-disabled');
    return;
  }

  downloadOriginalSrtBtn.disabled = false;
  downloadOriginalSrtBtn.classList.remove('btn-disabled');
  downloadTranslatedSrtBtn.disabled = false;
  downloadTranslatedSrtBtn.classList.remove('btn-disabled');

  if (currentJobId) {
    downloadOriginalSrtBtn.onclick = () => window.open(`/api/jobs/${currentJobId}/download/subtitle?type=original`, '_blank');
    downloadTranslatedSrtBtn.onclick = () => window.open(`/api/jobs/${currentJobId}/download/subtitle?type=translated`, '_blank');
  }

  const query = (subSearchInput.value || '').trim().toLowerCase();
  const filtered = currentSegments.filter((seg) => {
    if (!query) return true;
    const orig = (seg.original_text || seg.text || '').toLowerCase();
    const trans = (seg.translated_text || '').toLowerCase();
    return orig.includes(query) || trans.includes(query);
  });

  totalSubsCount.textContent = filtered.length;

  let totalChars = 0;
  let totalDur = 0;
  let maxCps = 0;

  filtered.forEach((s) => {
    const dur = Math.max(0.1, (s.end || 0) - (s.start || 0));
    const txt = activeSubtitleTab === 'translated' ? s.translated_text || s.text || '' : s.original_text || s.text || '';
    const cps = txt.length / dur;
    totalChars += txt.length;
    totalDur += dur;
    if (cps > maxCps) maxCps = cps;
  });

  avgCpsCount.textContent = totalDur > 0 ? (totalChars / totalDur).toFixed(1) : '—';
  maxCpsCount.textContent = maxCps > 0 ? maxCps.toFixed(1) : '—';

  transcriptList.innerHTML = filtered
    .map((seg, idx) => {
      const origText = seg.original_text || seg.text || '';
      const transText = seg.translated_text || '<span style="color: var(--text-dim); font-style: italic;">Chưa có bản dịch</span>';
      const displayText = activeSubtitleTab === 'translated' ? transText : origText;
      const dur = ((seg.end || 0) - (seg.start || 0)).toFixed(2);

      return `
        <div class="sub-item-row" data-start="${seg.start}" data-end="${seg.end}">
          <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
            <span class="sub-index">#${seg.index || idx + 1}</span>
            <span class="sub-time">${formatDuration(seg.start)} ➔ ${formatDuration(seg.end)} (${dur}s)</span>
          </div>
          <div class="sub-trans-col">${displayText}</div>
        </div>
      `;
    })
    .join('');

  // Click vào subtitle segment để nhảy timeline video
  transcriptList.querySelectorAll('.sub-item-row').forEach((row) => {
    row.addEventListener('click', () => {
      const start = parseFloat(row.dataset.start);
      if (!isNaN(start)) {
        videoPreview.currentTime = start;
        videoPreview.play();
      }
    });
  });
}

function renderFinalVideoOutput(job) {
  const artifacts = job.artifacts || {};
  const finalMeta = artifacts.final_video || job.video || {};
  const renderStage = job.stages && job.stages.render ? job.stages.render : {};
  const isRenderCompleted = renderStage.status === 'completed' && Boolean(finalMeta.available) && finalMeta.current !== false;
  const isReprocessing = Boolean(finalMeta.reprocessing) || ((job.status === 'processing' || renderStage.status === 'running' || renderStage.status === 'pending') && Boolean(finalMeta.available || finalMeta.revision));

  if (isRenderCompleted) {
    finalVideoEmpty.style.display = 'none';
    finalVideoContent.style.display = 'grid';
    finalVideoStatusBadge.textContent = '🟢 Sẵn sàng tải về';
    finalVideoStatusBadge.style.color = 'var(--emerald-400)';

    const targetUrl = finalMeta.video_url || `/api/jobs/${job.job_id}/result/video?v=${finalMeta.revision || 1}`;
    if (finalVideoPlayer.dataset.loadedUrl !== targetUrl) {
      finalVideoPlayer.pause();
      finalVideoPlayer.removeAttribute('src');
      finalVideoPlayer.load();
      finalVideoPlayer.src = targetUrl;
      finalVideoPlayer.load();
      finalVideoPlayer.dataset.loadedUrl = targetUrl;
      finalVideoPlayer.dataset.revision = String(finalMeta.revision || 1);
    }

    finalThumbDuration.textContent = finalMeta.duration_formatted || '00:00';
    finalVideoName.textContent = finalMeta.filename || 'final_dubbed.mp4';
    finalVideoRes.textContent = finalMeta.resolution || '1080p';
    finalVideoFormat.textContent = 'MP4 (H.264 + AAC)';
    finalVideoSize.textContent = finalMeta.size || '—';
    finalVideoDuration.textContent = finalMeta.duration_formatted || '—';
    finalVideoDate.textContent = new Date().toLocaleDateString('vi-VN');

    downloadVideoBtn.href = finalMeta.download_video_url || `/api/jobs/${job.job_id}/download/video?v=${finalMeta.revision || 1}`;
    downloadVideoBtn.setAttribute('download', finalMeta.filename || 'final_dubbed.mp4');
    downloadVideoBtn.disabled = false;
    downloadVideoBtn.classList.remove('btn-disabled');

    if (artifacts.subtitles && artifacts.subtitles.download_srt_url) {
      downloadSrtBtn.href = artifacts.subtitles.download_srt_url;
      downloadSrtBtn.disabled = false;
      downloadSrtBtn.classList.remove('btn-disabled');
    }
  } else if (isReprocessing) {
    finalVideoEmpty.style.display = 'none';
    finalVideoContent.style.display = 'grid';
    finalVideoStatusBadge.textContent = '🟡 Đang tạo lại...';
    finalVideoStatusBadge.style.color = '#fbbf24';

    finalVideoPlayer.pause();
    downloadVideoBtn.disabled = true;
    downloadVideoBtn.classList.add('btn-disabled');
    downloadVideoBtn.removeAttribute('href');
    if (downloadSrtBtn) {
      downloadSrtBtn.disabled = true;
      downloadSrtBtn.classList.add('btn-disabled');
    }
  } else {
    finalVideoEmpty.style.display = 'flex';
    finalVideoContent.style.display = 'none';
    finalVideoStatusBadge.textContent = '⚪ Chờ xử lý';
    finalVideoStatusBadge.style.color = 'var(--text-dim)';
    finalVideoPlayer.pause();
    finalVideoPlayer.removeAttribute('src');
    finalVideoPlayer.dataset.loadedUrl = '';
    finalVideoPlayer.dataset.revision = '';
    downloadVideoBtn.disabled = true;
    downloadVideoBtn.classList.add('btn-disabled');
    downloadVideoBtn.removeAttribute('href');
  }
}

function renderBatchResults(batch) {
  if (!batch || !batch.jobs_detail || batch.jobs_detail.length <= 1) {
    batchResultsWrapper.style.display = 'none';
    return;
  }

  batchResultsWrapper.style.display = 'block';
  batchResultsList.innerHTML = batch.jobs_detail
    .map((j, idx) => {
      const v = j.video || j.video_info || {};
      const name = v.filename || `Video #${idx + 1}`;
      const isDone = j.status === 'completed';
      const isErr = j.status === 'failed';

      let statusPill = `<span class="badge-status-running">Đang xử lý</span>`;
      if (isDone) statusPill = `<span class="badge-status-completed">✓ Xong</span>`;
      else if (isErr) statusPill = `<span class="badge-status-failed">✕ Lỗi</span>`;

      const downloadMp4 = isDone
        ? `<a href="/api/jobs/${j.job_id}/download/video" class="btn-action-small" download>⬇ MP4</a>`
        : '';
      const downloadSrt = isDone
        ? `<a href="/api/jobs/${j.job_id}/download/subtitle" class="btn-action-small" download>📄 SRT</a>`
        : '';

      return `
        <div class="batch-result-card">
          <div class="batch-card-left">
            <div class="batch-card-name">#${idx + 1}. ${escapeHtml(name)}</div>
            <div class="batch-card-meta">${statusPill} • ${v.duration_formatted || '—'}</div>
          </div>
          <div class="batch-card-actions">
            ${downloadMp4}
            ${downloadSrt}
          </div>
        </div>
      `;
    })
    .join('');
}

// ================= HISTORY DRAWER (Phase 2 / TEST 2, TEST 15) =================
async function openHistoryDrawer() {
  historyDrawerBackdrop.classList.add('open');
  historyDrawer.classList.add('open');
  historyListContainer.innerHTML = `
    <div class="empty-state-box">
      <div class="empty-icon">⏳</div>
      <div class="empty-title">Đang nạp lịch sử...</div>
    </div>
  `;

  try {
    const res = await apiClient.getJobs();
    allHistoryJobs = res.jobs || [];
    renderHistoryList();
  } catch (err) {
    historyListContainer.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-icon">⚠️</div>
        <div class="empty-title">Không thể tải lịch sử</div>
        <div class="empty-desc">${escapeHtml(err.message)}</div>
      </div>
    `;
  }
}

function closeHistoryDrawer() {
  historyDrawerBackdrop.classList.remove('open');
  historyDrawer.classList.remove('open');
}

function renderHistoryList() {
  const query = (historySearchInput.value || '').trim().toLowerCase();
  const filtered = allHistoryJobs.filter((j) => {
    if (!query) return true;
    return (j.filename || '').toLowerCase().includes(query) || (j.job_id || '').toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    historyListContainer.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-icon">📁</div>
        <div class="empty-title">Không tìm thấy tác vụ nào</div>
      </div>
    `;
    return;
  }

  historyListContainer.innerHTML = filtered
    .map((j) => {
      let statusBadge = `<span class="badge-status-completed">✓ Hoàn tất</span>`;
      if (j.status === 'failed') statusBadge = `<span class="badge-status-failed">✕ Lỗi</span>`;
      else if (j.status === 'processing') statusBadge = `<span class="badge-status-running">⏳ Đang chạy</span>`;

      return `
        <div class="history-card" data-job-id="${j.job_id}">
          <div class="history-card-header">
            <div class="history-card-title">🎬 ${escapeHtml(j.filename || 'Video')}</div>
            ${statusBadge}
          </div>
          <div class="history-card-body">
            <span>⏱ ${j.duration_formatted || '—'}</span>
            <span>🌐 Đích: ${(j.target_language || 'vi').toUpperCase()}</span>
            <span>📅 ${new Date(j.created_at).toLocaleString('vi-VN')}</span>
          </div>
          <div class="history-card-actions">
            <button type="button" class="btn-ghost-dark btn-small btn-load-job" data-job-id="${j.job_id}">
              <span>📂</span> Mở lại
            </button>
            <button type="button" class="btn-text-dim btn-small btn-del-job" data-job-id="${j.job_id}" style="color: #f87171;">
              <span>🗑️</span> Xóa
            </button>
          </div>
        </div>
      `;
    })
    .join('');

  historyListContainer.querySelectorAll('.btn-load-job').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const jobId = btn.dataset.jobId;
      restoreJobState(jobId);
      closeHistoryDrawer();
      showToast(`Đã khôi phục Job ${jobId.slice(0, 8)}...`);
    });
  });

  historyListContainer.querySelectorAll('.btn-del-job').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const jobId = btn.dataset.jobId;
      if (confirm('Bạn có chắc muốn xóa Job này khỏi lịch sử?')) {
        try {
          await apiClient.deleteJob(jobId);
          allHistoryJobs = allHistoryJobs.filter((item) => item.job_id !== jobId);
          renderHistoryList();
          showToast('Đã xóa Job thành công');
        } catch (err) {
          showToast('Lỗi khi xóa Job', 'error');
        }
      }
    });
  });
}

// ================= RESET WORKSPACE TO NO_JOB =================
function resetWorkspaceToNoJob() {
  workspaceGeneration++; // Tăng generation token để tự động hủy mọi pending response cũ (Section 5)
  workspaceMode = 'no_job'; // Explicit workspace state (Section 10)
  
  stopPolling();
  if (activeBatchPollTimer) {
    clearInterval(activeBatchPollTimer);
    activeBatchPollTimer = null;
  }

  // 1. Clear Central State FIRST before DOM
  clearCentralJobState();

  // 2. Persist NO_JOB and purge local storage
  localStorage.setItem('workspace_mode', 'no_job');
  localStorage.removeItem('last_job_id');
  localStorage.removeItem('last_batch_id');

  // 3. Render clean NO_JOB DOM state
  renderNoJobState();
}

function renderNoJobState() {
  // 1. Reset Video Player & Dropzone
  videoPreview.pause();
  videoPreview.removeAttribute('src');
  videoPreview.load();
  videoPreview.style.display = 'none';
  dropzone.style.display = 'flex';
  fileInput.value = '';

  // 2. Reset Video Badges & Metadata
  videoBadgeName.textContent = '🎬 Chưa có video';
  videoBadgeRes.textContent = '🔲 —';
  videoBadgeDuration.textContent = '⏱ —';
  videoBadgeFps.textContent = '🎬 —';

  videoName.textContent = '—';
  videoFormat.textContent = '—';
  videoDuration.textContent = '—';
  videoFps.textContent = '—';
  videoResolution.textContent = '—';
  videoRatio.textContent = '—';
  videoSize.textContent = '—';
  videoUploadDate.textContent = '—';

  // 3. Reset Progress Bar & Status (Full Reset)
  progressBox.style.display = 'none';
  progressBarFill.style.width = '0%';
  progressBarFill.style.background = 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)';
  progressPercent.textContent = '0%';
  progressStatus.textContent = 'Chờ xử lý';

  // 4. Hide Retry & Error UI and reset buttons
  retryActionBox.style.display = 'none';
  retryErrorMessage.textContent = '';
  btnRetryFailed.disabled = false;
  btnRerunAll.disabled = false;
  btnRetryFailed.innerHTML = '<span>🔄</span> Thử lại từ đoạn lỗi';
  btnRerunAll.innerHTML = '<span>🔁</span> Chạy lại toàn bộ';

  // 5. Reset Stepper, Pipeline Pills, Log Table & Subtitle Data
  renderPipelinePills({});
  renderStepperItems({});
  renderProcessingLogs({});
  currentSegments = [];
  translatedSegments = [];
  subtitleData = [];
  if (subSearchInput) subSearchInput.value = '';
  renderSubtitles();

  // 6. Reset Final Output Card & Download Actions
  finalVideoEmpty.style.display = 'flex';
  finalVideoContent.style.display = 'none';
  finalVideoStatusBadge.textContent = '⚪ Chờ xử lý';
  finalVideoStatusBadge.style.color = 'var(--text-dim)';
  finalVideoPlayer.pause();
  finalVideoPlayer.removeAttribute('src');
  finalVideoPlayer.load();
  finalThumbDuration.textContent = '00:00';
  finalVideoName.textContent = '—';
  finalVideoRes.textContent = '—';
  finalVideoFormat.textContent = '—';
  finalVideoSize.textContent = '—';
  finalVideoDuration.textContent = '—';
  finalVideoDate.textContent = '—';

  downloadVideoBtn.removeAttribute('href');
  downloadVideoBtn.disabled = true;
  downloadVideoBtn.classList.add('btn-disabled');

  downloadSrtBtn.removeAttribute('href');
  downloadSrtBtn.disabled = true;
  downloadSrtBtn.classList.add('btn-disabled');

  // 7. Reset Batch UI
  batchQueueBar.style.display = 'none';
  batchResultsWrapper.style.display = 'none';
  queueCountBadge.textContent = '0/5 video';
  queueTotalProgress.textContent = '0%';
  queuePillsList.innerHTML = '';
  batchResultsList.innerHTML = '';

  // 8. Reset Primary START Button (Disabled khi chưa có video)
  runPipelineBtn.disabled = true;
  runPipelineBtn.classList.add('btn-disabled');
  runPipelineBtn.innerHTML = '<span>🚀</span> BẮT ĐẦU XỬ LÝ';

  // 9. Hide Subtitle Overlay in Clean NO_JOB state
  if (subtitleLiveOverlay) {
    subtitleLiveOverlay.style.display = 'none';
  }
}

async function restoreJobState(jobId) {
  try {
    const currentGen = ++workspaceGeneration;
    const job = await apiClient.getJob(jobId);
    if (!job || !job.job_id || workspaceGeneration !== currentGen) {
      resetWorkspaceToNoJob();
      return;
    }

    workspaceMode = 'job';
    currentJobId = jobId;
    currentBatchId = null;
    batchJobs = [job];
    activeJobIndex = 0;
    localStorage.setItem('workspace_mode', 'job');
    localStorage.setItem('last_job_id', jobId);
    localStorage.removeItem('last_batch_id');

    batchQueueBar.style.display = 'none';
    if (job.video) {
      bindVideoToPreview(job.video.preview_url || `/api/jobs/${jobId}/video`, job.video);
    }
    renderJobState(job);

    if (job.status === 'processing') {
      startJobPolling(jobId);
    }
  } catch (e) {
    console.warn(`Không thể khôi phục job ${jobId}, tự động reset NO_JOB:`, e);
    resetWorkspaceToNoJob();
  }
}

async function restoreBatchState(batchId) {
  try {
    const currentGen = ++workspaceGeneration;
    const batch = await apiClient.getBatch(batchId);
    if (!batch || !batch.batch_id || !batch.jobs_detail || batch.jobs_detail.length === 0 || workspaceGeneration !== currentGen) {
      resetWorkspaceToNoJob();
      return;
    }

    workspaceMode = 'batch';
    currentBatchId = batchId;
    batchJobs = batch.jobs_detail || [];
    activeJobIndex = batch.current_job_index >= 0 ? batch.current_job_index : 0;
    currentJobId = batch.current_job_id || (batchJobs[0] ? batchJobs[0].job_id : null);

    localStorage.setItem('workspace_mode', 'batch');
    localStorage.setItem('last_batch_id', batchId);
    if (currentJobId) localStorage.setItem('last_job_id', currentJobId);

    renderBatchQueueBar();
    renderBatchResults(batch);

    if (batchJobs[activeJobIndex]) {
      const curJob = batchJobs[activeJobIndex];
      if (curJob.video) {
        bindVideoToPreview(curJob.video.preview_url || `/api/jobs/${curJob.job_id}/video`, curJob.video);
      }
      renderJobState(curJob);
    }

    if (batch.status === 'processing') {
      startBatchPolling(batchId);
    }
  } catch (e) {
    console.warn(`Không thể khôi phục batch ${batchId}, tự động reset NO_JOB:`, e);
    resetWorkspaceToNoJob();
  }
}

// ================= NEW VIDEO WORKFLOW (Phase 4 / TEST 6) =================
function handleNewVideoWorkflow() {
  isProcessing = false;
  resetWorkspaceToNoJob();
  showToast('Workspace đã sẵn sàng cho video mới.');
}

// ================= VOICE PREVIEW =================
async function handlePreviewVoice() {
  const voice = voiceSelect.value;
  const speedRate = speedRateValue.textContent;
  previewVoiceBtn.disabled = true;
  previewVoiceBtn.innerHTML = '<span>⏳</span> Đang tạo...';

  try {
    const audioUrl = await apiClient.previewVoice(
      'Một bí mật kinh hoàng vừa được hé lộ, và đây là điều mà không ai có thể ngờ tới!',
      voice,
      speedRate
    );

    if (previewAudioObj) {
      previewAudioObj.pause();
      previewAudioObj = null;
    }

    previewAudioObj = new Audio(audioUrl);
    previewAudioObj.play();
    previewAudioObj.onended = () => {
      previewVoiceBtn.disabled = false;
      previewVoiceBtn.innerHTML = '<span>✨</span> Nghe thử giọng này';
    };
  } catch (err) {
    showToast(err.message || 'Lỗi nghe thử giọng đọc', 'error');
    previewVoiceBtn.disabled = false;
    previewVoiceBtn.innerHTML = '<span>✨</span> Nghe thử giọng này';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
