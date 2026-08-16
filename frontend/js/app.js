import { apiClient } from './api.js';

// ================= DOM ELEMENTS =================
// 1. Upload & Video Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const selectBtn = document.getElementById('selectBtn');
const videoPreview = document.getElementById('videoPreview');
const videoFrameWrapper = document.getElementById('videoFrameWrapper');
const subtitleLiveOverlay = document.getElementById('subtitleLiveOverlay');

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
let workspaceMode = 'no_job'; // 'no_job' | 'job' | 'batch' (Section 10)
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
let isGeminiConfigured = false;
let subtitlePosition = { x: 0.50, y: 0.88 }; // Tọa độ tương đối chuẩn hóa (0.0 đến 1.0)
let workspaceGeneration = 0; // Generation Token chống race condition stale response (Section 5)

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
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'error' : ''}`;
  toast.innerHTML = `<span>${type === 'error' ? '❌' : '✓'}</span><span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
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
document.addEventListener('DOMContentLoaded', async () => {
  initEventListeners();
  updateSubtitleVisibilityAndPreview();

  // Kiểm tra sức khỏe hệ thống & Gemini API status
  try {
    const health = await apiClient.checkHealth();
    if (health.status === 'healthy') {
      systemAlertText.textContent = 'Hệ thống sẵn sàng: FFmpeg, Faster-Whisper, Gemini AI, Edge-TTS & ASS Burn-in đã kích hoạt.';
    } else {
      systemAlertText.textContent = `Cảnh báo: ${health.message || 'Một số module chưa sẵn sàng'}`;
      systemAlert.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    }
  } catch (e) {
    console.warn('Lỗi kiểm tra hệ thống:', e);
  }

  // Tải trạng thái Gemini API Key đã lưu (TEST 36, 37)
  await loadGeminiStatus();

  // Restore Job hoặc Batch sau khi F5 (CASE A: Đang xem Job hợp lệ / CASE B: NO_JOB)
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
});

// ================= GEMINI API KEY MANAGEMENT =================
async function loadGeminiStatus() {
  try {
    const res = await apiClient.getGeminiStatus();
    isGeminiConfigured = res.configured;
    if (res.configured) {
      geminiKeyStatusBox.style.display = 'flex';
      geminiKeyInputBox.style.display = 'none';
      geminiStatusText.textContent = 'Gemini API: Đã cấu hình';
      if (res.source === 'env') {
        geminiStatusText.textContent = 'Gemini API: Cấu hình qua .env';
      }
    } else {
      geminiKeyStatusBox.style.display = 'none';
      geminiKeyInputBox.style.display = 'block';
      btnCancelGeminiKey.style.display = 'none';
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
  selectBtn.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('click', (e) => {
    if (e.target !== selectBtn) fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(Array.from(e.target.files));
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

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(Array.from(e.dataTransfer.files));
    }
  });

  // Slider Badges
  speedRateRange.addEventListener('input', () => {
    const val = parseInt(speedRateRange.value);
    speedRateValue.textContent = val >= 0 ? `+${val}%` : `${val}%`;
  });

  pitchRange.addEventListener('input', () => {
    const val = parseInt(pitchRange.value);
    pitchValue.textContent = val >= 0 ? `+${val}Hz` : `${val}Hz`;
  });

  voiceVolumeRange.addEventListener('input', () => {
    voiceVolumeValue.textContent = `${voiceVolumeRange.value}%`;
  });

  bgVolumeRange.addEventListener('input', () => {
    bgVolumeValue.textContent = `${bgVolumeRange.value}%`;
  });

  // Gemini API Key Buttons
  btnSaveGeminiKey.addEventListener('click', handleSaveGeminiKey);
  btnChangeGeminiKey.addEventListener('click', () => {
    geminiKeyStatusBox.style.display = 'none';
    geminiKeyInputBox.style.display = 'block';
    btnCancelGeminiKey.style.display = 'inline-block';
    geminiApiKeyInput.focus();
  });
  btnCancelGeminiKey.addEventListener('click', () => {
    geminiKeyInputBox.style.display = 'none';
    geminiKeyStatusBox.style.display = 'flex';
    geminiApiKeyInput.value = '';
  });
  btnDeleteGeminiKey.addEventListener('click', handleDeleteGeminiKey);

  // Subtitle Toggle & Subtitle Mode (Requirements 15, 16, 17, 18)
  optSubtitle.addEventListener('change', () => {
    updateSubtitleVisibilityAndPreview();
  });

  subModeSelect.addEventListener('change', () => {
    updateSubtitleVisibilityAndPreview();
  });

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
      if (elem === subTextColor) subTextColorLabel.textContent = subTextColor.value.toUpperCase();
      if (elem === subOutlineColor) subOutlineColorLabel.textContent = subOutlineColor.value.toUpperCase();
      if (elem === subOutlineWidth) subOutlineWidthValue.textContent = `${subOutlineWidth.value}px`;
      updateSubtitleOverlayStyles();
    });
  });

  resetSubStyleBtn.addEventListener('click', () => {
    subFontFamily.value = 'Arial';
    subTextColor.value = '#ffffff';
    subTextColorLabel.textContent = '#FFFFFF';
    subOutlineColor.value = '#000000';
    subOutlineColorLabel.textContent = '#000000';
    subFontSize.value = 36;
    subOutlineWidth.value = 2.5;
    subOutlineWidthValue.textContent = '2.5px';
    subBoldCheckbox.checked = true;
    subShadowCheckbox.checked = true;
    subtitlePosition = { x: 0.50, y: 0.88 };
    updateSubtitleOverlayStyles();
    showToast('Đã khôi phục style phụ đề mặc định (x=50%, y=88%)');
  });

  // Synchronize Live Subtitle Overlay on Video Timeupdate
  videoPreview.addEventListener('timeupdate', () => {
    updateSubtitleOverlayText();
  });

  // Khởi tạo các sự kiện kéo thả và phóng to trực tiếp trên video preview
  initSubtitleDraggableEvents();

  // Whisper STT Checkbox dependency
  optSTT.addEventListener('change', () => {
    if (optSTT.checked) {
      whisperModelSelect.disabled = false;
      whisperModelSubOption.style.opacity = '1';
      whisperModelSubOption.style.pointerEvents = 'auto';
    } else {
      whisperModelSelect.disabled = true;
      whisperModelSubOption.style.opacity = '0.4';
      whisperModelSubOption.style.pointerEvents = 'none';
    }
  });

  // Voice Preview
  previewVoiceBtn.addEventListener('click', handlePreviewVoice);

  // Reset Config
  resetConfigBtn.addEventListener('click', () => {
    sourceLangSelect.value = 'auto';
    targetLangSelect.value = 'vi';
    translationStyleSelect.value = 'movie_review_spoken_vi';
    voiceSelect.value = 'vi-VN-NamMinhNeural_tiktok_review';
    speedRateRange.value = 15;
    speedRateValue.textContent = '+15%';
    pitchRange.value = 2;
    pitchValue.textContent = '+2Hz';
    voiceVolumeRange.value = 120;
    voiceVolumeValue.textContent = '120%';
    bgVolumeRange.value = 15;
    bgVolumeValue.textContent = '15%';
    showToast('Đã đặt lại cấu hình lồng tiếng');
  });

  // Primary Action Button (Unified Run Pipeline)
  runPipelineBtn.addEventListener('click', handleRunPipeline);

  // Retry Handlers (Phase 1)
  btnRetryFailed.addEventListener('click', () => handleRetry(true));
  btnRerunAll.addEventListener('click', () => handleRetry(false));

  // New Video Workflow (Phase 4)
  btnNewVideo.addEventListener('click', handleNewVideoWorkflow);
  btnHeaderNewVideo.addEventListener('click', handleNewVideoWorkflow);

  // Subtitle Tabs & Search
  tabOriginal.addEventListener('click', () => {
    activeSubtitleTab = 'original';
    tabOriginal.classList.add('active');
    tabTranslated.classList.remove('active');
    renderSubtitles();
  });

  tabTranslated.addEventListener('click', () => {
    activeSubtitleTab = 'translated';
    tabTranslated.classList.add('active');
    tabOriginal.classList.remove('active');
    renderSubtitles();
  });

  subSearchInput.addEventListener('input', () => renderSubtitles());
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

  // History Drawer (Phase 2)
  btnOpenHistory.addEventListener('click', openHistoryDrawer);
  btnCloseHistory.addEventListener('click', closeHistoryDrawer);
  historyDrawerBackdrop.addEventListener('click', closeHistoryDrawer);
  historySearchInput.addEventListener('input', renderHistoryList);
}

// ================= DIRECT MANIPULATION SUBTITLE OVERLAY (DRAG & RESIZE) =================
let isDraggingSub = false;
let isResizingSub = false;
let dragStartX = 0;
let dragStartY = 0;
let initialSubPosX = 0.50;
let initialSubPosY = 0.88;
let initialSubFontSize = 36;

function initSubtitleDraggableEvents() {
  if (!subtitleLiveOverlay) return;

  // Render container nếu chưa có
  ensureSubtitleOverlayElements();

  const box = document.getElementById('subtitleDraggableBox');
  const resizeHandle = document.getElementById('subtitleResizeHandle');
  if (!box || !resizeHandle) return;

  // 1. Drag & Move Subtitle
  const onMouseDownDrag = (e) => {
    if (e.target === resizeHandle) return;
    if (e.button !== 0) return; // Chỉ chuột trái
    e.preventDefault();
    isDraggingSub = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    initialSubPosX = subtitlePosition.x;
    initialSubPosY = subtitlePosition.y;
    box.classList.add('is-dragging');

    window.addEventListener('mousemove', onMouseMoveDrag);
    window.addEventListener('mouseup', onMouseUpDrag);
  };

  const onMouseMoveDrag = (e) => {
    if (!isDraggingSub) return;
    const rect = videoFrameWrapper ? videoFrameWrapper.getBoundingClientRect() : { width: 640, height: 360 };
    const dx = (e.clientX - dragStartX) / Math.max(1, rect.width);
    const dy = (e.clientY - dragStartY) / Math.max(1, rect.height);

    // Giới hạn trong khung hình (0.06 đến 0.94)
    subtitlePosition.x = Math.max(0.06, Math.min(0.94, initialSubPosX + dx));
    subtitlePosition.y = Math.max(0.06, Math.min(0.94, initialSubPosY + dy));

    box.style.left = `${(subtitlePosition.x * 100).toFixed(2)}%`;
    box.style.top = `${(subtitlePosition.y * 100).toFixed(2)}%`;
  };

  const onMouseUpDrag = () => {
    if (isDraggingSub) {
      isDraggingSub = false;
      box.classList.remove('is-dragging');
      window.removeEventListener('mousemove', onMouseMoveDrag);
      window.removeEventListener('mouseup', onMouseUpDrag);
    }
  };

  box.addEventListener('mousedown', onMouseDownDrag);

  // 2. Resize Handle (Scale font size trực tiếp)
  const onMouseDownResize = (e) => {
    e.stopPropagation();
    e.preventDefault();
    isResizingSub = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    initialSubFontSize = parseInt(subFontSize.value) || 36;
    resizeHandle.classList.add('is-resizing');

    window.addEventListener('mousemove', onMouseMoveResize);
    window.addEventListener('mouseup', onMouseUpResize);
  };

  const onMouseMoveResize = (e) => {
    if (!isResizingSub) return;
    const delta = (e.clientX - dragStartX) + (e.clientY - dragStartY);
    const newSize = Math.max(18, Math.min(72, Math.round(initialSubFontSize + delta * 0.35)));
    subFontSize.value = newSize;
    updateSubtitleOverlayStyles();
  };

  const onMouseUpResize = () => {
    if (isResizingSub) {
      isResizingSub = false;
      resizeHandle.classList.remove('is-resizing');
      window.removeEventListener('mousemove', onMouseMoveResize);
      window.removeEventListener('mouseup', onMouseUpResize);
    }
  };

  resizeHandle.addEventListener('mousedown', onMouseDownResize);
}

function ensureSubtitleOverlayElements() {
  if (!subtitleLiveOverlay) return;
  if (!document.getElementById('subtitleDraggableBox')) {
    subtitleLiveOverlay.innerHTML = `
      <div class="subtitle-draggable-box" id="subtitleDraggableBox" title="Kéo giữ để di chuyển vị trí phụ đề">
        <span class="subtitle-text-content" id="subtitleTextContent">Đây là phụ đề</span>
        <div class="subtitle-resize-handle" id="subtitleResizeHandle" title="Kéo để phóng to/thu nhỏ cỡ chữ"></div>
      </div>
    `;
  }
}

function updateSubtitleVisibilityAndPreview() {
  const isEnabled = optSubtitle ? optSubtitle.checked : true;
  const hasVideoLoaded = Boolean(
    videoPreview &&
    videoPreview.style.display !== 'none' &&
    (videoPreview.src || (currentJobId && dropzone && dropzone.style.display === 'none'))
  );

  if (isEnabled) {
    if (subtitleStyleCard) {
      subtitleStyleCard.style.opacity = '1';
      subtitleStyleCard.style.pointerEvents = 'auto';
    }
    if (subModeSubOption) {
      subModeSubOption.style.opacity = '1';
      subModeSubOption.style.pointerEvents = 'auto';
    }
    if (subtitleLiveOverlay) {
      ensureSubtitleOverlayElements();
      if (hasVideoLoaded) {
        subtitleLiveOverlay.style.display = 'block';
        updateSubtitleOverlayStyles();
        updateSubtitleOverlayText();
      } else {
        subtitleLiveOverlay.style.display = 'none';
      }
    }
  } else {
    if (subtitleStyleCard) {
      subtitleStyleCard.style.opacity = '0.4';
      subtitleStyleCard.style.pointerEvents = 'none';
    }
    if (subModeSubOption) {
      subModeSubOption.style.opacity = '0.4';
      subModeSubOption.style.pointerEvents = 'none';
    }
    if (subtitleLiveOverlay) {
      subtitleLiveOverlay.style.display = 'none';
    }
  }
}

function updateSubtitleOverlayStyles() {
  if (!subtitleLiveOverlay || (optSubtitle && !optSubtitle.checked)) return;

  ensureSubtitleOverlayElements();

  const box = document.getElementById('subtitleDraggableBox');
  const textContent = document.getElementById('subtitleTextContent');
  if (!box || !textContent) return;

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

  // Áp dụng vị trí tương đối trực tiếp (0.0 đến 1.0)
  box.style.left = `${(subtitlePosition.x * 100).toFixed(2)}%`;
  box.style.top = `${(subtitlePosition.y * 100).toFixed(2)}%`;
  box.style.transform = 'translate(-50%, -50%)';

  // Typography & Styling
  textContent.style.fontFamily = `"${font}", sans-serif`;
  textContent.style.fontSize = `${effectiveSize}px`;
  textContent.style.fontWeight = bold ? '700' : '400';
  textContent.style.color = color;

  // Outline & Drop shadow
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
  if (!subtitleLiveOverlay || (optSubtitle && !optSubtitle.checked)) return;

  ensureSubtitleOverlayElements();
  const textContent = document.getElementById('subtitleTextContent');
  if (!textContent) return;

  // Nếu đã có phụ đề thật và video đang phát: Đồng bộ theo video.currentTime
  if (currentSegments && currentSegments.length > 0 && videoPreview && videoPreview.currentTime > 0) {
    const curTime = videoPreview.currentTime;
    const activeSeg = currentSegments.find((s) => curTime >= s.start && curTime <= s.end);

    if (activeSeg) {
      const txt = activeSeg.translated_text || activeSeg.text || activeSeg.original_text || '';
      textContent.textContent = txt;
      textContent.style.display = 'inline-block';
      return;
    } else {
      textContent.textContent = '';
      textContent.style.display = 'none';
      return;
    }
  }

  // Khi chưa phát hoặc chưa có transcript dịch: Hiển thị câu mẫu để người dùng kéo thả & căn chỉnh
  textContent.textContent = 'Đây là phụ đề';
  textContent.style.display = 'inline-block';
}

function getSubtitleStyleConfig() {
  return {
    font_family: subFontFamily ? subFontFamily.value || 'Arial' : 'Arial',
    font_size: subFontSize ? parseInt(subFontSize.value) || 36 : 36,
    primary_color: subTextColor ? subTextColor.value || '#FFFFFF' : '#FFFFFF',
    outline_color: subOutlineColor ? subOutlineColor.value || '#000000' : '#000000',
    outline_width: subOutlineWidth ? parseFloat(subOutlineWidth.value) || 2.5 : 2.5,
    position_x: subtitlePosition.x,
    position_y: subtitlePosition.y,
    bold: subBoldCheckbox ? subBoldCheckbox.checked : true,
    shadow: subShadowCheckbox ? (subShadowCheckbox.checked ? 1.0 : 0.0) : 1.0,
  };
}

// ================= FILE UPLOAD & BATCH MANAGEMENT (NO AUTO-RUN) =================
async function handleFilesSelected(files) {
  if (!files || files.length === 0) return;

  // 1. Luôn Reset sạch workspace trước khi thực hiện upload file mới (Unified cleanup)
  resetWorkspaceToNoJob();

  // Validate số lượng file (1 đến 5 video)
  if (files.length > 5) {
    showToast('Tối đa 5 video cho mỗi lượt xử lý (TEST 5)', 'error');
    return;
  }

  // Validate định dạng
  for (const f of files) {
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      showToast(`File "${f.name}" không hợp lệ. Chỉ chấp nhận MP4, MOV, MKV, WEBM.`, 'error');
      return;
    }
  }

  // Hiển thị upload progress
  progressBox.style.display = 'block';
  progressStatus.textContent = files.length > 1 ? `Đang tải lên ${files.length} video...` : 'Đang tải video lên máy chủ...';
  progressBarFill.style.width = '10%';
  progressPercent.textContent = '10%';
  dropzone.style.display = 'none';

  try {
    if (files.length === 1) {
      // 1 Video Upload (100% Tương thích ngược)
      const res = await apiClient.uploadVideo(files[0], (pct) => {
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
      });

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
      bindVideoToPreview(files[0], res.video);

      // Đưa giao diện về trạng thái UPLOADED / READY (TUYỆT ĐỐI KHÔNG TỰ CHẠY PIPELINE)
      renderUploadedReadyState(res);
      showToast('Tải lên video thành công. Hãy chọn cấu hình và nhấn BẮT ĐẦU XỬ LÝ.');
    } else {
      // Batch Upload 2-5 Videos (Phase 3)
      const res = await apiClient.uploadBatchVideos(files, (pct) => {
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
      });

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
      bindVideoToPreview(files[0], batchJobs[0].video);

      // Đưa giao diện về trạng thái UPLOADED / READY
      renderUploadedReadyState(batchJobs[0]);
      showToast(`Đã tải lên ${batchJobs.length} video vào hàng đợi. Sẵn sàng xử lý.`);
    }
  } catch (err) {
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

  // 8. Cập nhật Live Overlay
  updateSubtitleVisibilityAndPreview();
}

function bindVideoToPreview(fileOrUrl, videoMeta) {
  if (typeof fileOrUrl === 'string') {
    videoPreview.src = fileOrUrl;
  } else if (fileOrUrl instanceof File) {
    videoPreview.src = URL.createObjectURL(fileOrUrl);
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
  };

  try {
    if (currentBatchId && batchJobs.length > 1) {
      // Chạy Batch tuần tự (concurrency = 1)
      await apiClient.processBatch(currentBatchId, config);
      showToast(`Đã bắt đầu xử lý tuần tự ${batchJobs.length} video.`);
      startBatchPolling(currentBatchId);
    } else {
      // Chạy 1 Job đơn lẻ
      await apiClient.processPipeline(currentJobId, config);
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
  };

  try {
    const res = await apiClient.retryJob(currentJobId, {
      resume_from_failed: resumeFromFailed,
      pipeline_config: config,
    });
    retryActionBox.style.display = 'none';
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
    progressStatus.textContent = 'Đang thực thi pipeline...';
    progressBarFill.style.background = 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)';
  }

  // 2. Retry Box (Phase 1)
  if (isFailed) {
    retryActionBox.style.display = 'block';
    retryErrorMessage.textContent = `Tác vụ bị lỗi: ${job.error || 'Chi tiết trong nhật ký'}`;
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

  // 7. Live Subtitle Overlay Preview
  updateSubtitleVisibilityAndPreview();

  // 8. Start Button State
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
        const hasPct = st.progress !== null && st.progress !== undefined && !isNaN(st.progress);
        const pct = hasPct ? ` (${Math.round(st.progress)}%)` : '';
        statusBadge = `<span class="badge-status-running">⏳ Đang xử lý${pct}</span>`;
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
    downloadOriginalSrtBtn.onclick = () => window.open(`/api/jobs/${currentJobId}/download/subtitle`, '_blank');
    downloadTranslatedSrtBtn.onclick = () => window.open(`/api/jobs/${currentJobId}/download/subtitle`, '_blank');
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
  const isRenderCompleted = job.stages && job.stages.render && job.stages.render.status === 'completed' && finalMeta.available;

  if (isRenderCompleted) {
    finalVideoEmpty.style.display = 'none';
    finalVideoContent.style.display = 'grid';
    finalVideoStatusBadge.textContent = '🟢 Sẵn sàng tải về';
    finalVideoStatusBadge.style.color = 'var(--emerald-400)';

    finalVideoPlayer.src = finalMeta.video_url || `/api/jobs/${job.job_id}/result/video`;
    finalThumbDuration.textContent = finalMeta.duration_formatted || '00:00';
    finalVideoName.textContent = finalMeta.filename || 'final_dubbed.mp4';
    finalVideoRes.textContent = finalMeta.resolution || '1080p';
    finalVideoFormat.textContent = 'MP4 (H.264 + AAC)';
    finalVideoSize.textContent = finalMeta.size || '—';
    finalVideoDuration.textContent = finalMeta.duration_formatted || '—';
    finalVideoDate.textContent = new Date().toLocaleDateString('vi-VN');

    downloadVideoBtn.href = finalMeta.download_video_url || `/api/jobs/${job.job_id}/download/video`;
    downloadVideoBtn.disabled = false;
    downloadVideoBtn.classList.remove('btn-disabled');

    if (artifacts.subtitles && artifacts.subtitles.download_srt_url) {
      downloadSrtBtn.href = artifacts.subtitles.download_srt_url;
      downloadSrtBtn.disabled = false;
      downloadSrtBtn.classList.remove('btn-disabled');
    }
  } else {
    finalVideoEmpty.style.display = 'flex';
    finalVideoContent.style.display = 'none';
    finalVideoStatusBadge.textContent = '⚪ Chờ xử lý';
    finalVideoStatusBadge.style.color = 'var(--text-dim)';
    downloadVideoBtn.disabled = true;
    downloadVideoBtn.classList.add('btn-disabled');
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
