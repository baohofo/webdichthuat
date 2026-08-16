/**
 * API Client Module - Quản lý việc kết nối và trao đổi dữ liệu với Backend FastAPI
 */

const API_BASE = '/api';

export const apiClient = {
  /**
   * Kiểm tra tình trạng hoạt động của hệ thống và FFmpeg
   */
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Lỗi khi kiểm tra sức khỏe hệ thống:', error);
      return {
        status: 'error',
        ffmpeg_installed: false,
        message: 'Không thể kết nối đến máy chủ Backend.'
      };
    }
  },

  /**
   * Upload video lên backend và theo dõi tiến trình % thực tế
   * @param {File} file - File video cần tải lên
   * @param {Function} onProgress - Callback nhận phần trăm tải lên (0-100)
   * @returns {Promise<Object>}
   */
  uploadVideo(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      // Lắng nghe tiến trình upload thực tế
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && typeof onProgress === 'function') {
          const percentCompleted = Math.round((event.loaded * 100) / event.total);
          onProgress(percentCompleted);
        }
      });

      // Lắng nghe kết quả hoàn thành
      xhr.addEventListener('load', () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.detail || `Lỗi máy chủ: ${xhr.status}`));
          }
        } catch (e) {
          reject(new Error(`Phản hồi không hợp lệ từ máy chủ (${xhr.status})`));
        }
      });

      // Lắng nghe lỗi mạng
      xhr.addEventListener('error', () => {
        reject(new Error('Mất kết nối mạng trong quá trình upload file.'));
      });

      // Lắng nghe timeout hoặc abort
      xhr.addEventListener('abort', () => {
        reject(new Error('Yêu cầu upload đã bị hủy.'));
      });

      xhr.open('POST', `${API_BASE}/upload`, true);
      xhr.send(formData);
    });
  },

  /**
   * Tra cứu thông tin một Job theo Job ID
   */
  async getJob(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Thực hiện nhận diện giọng nói (STT) bằng Faster-Whisper
   * @param {string} jobId
   * @param {string} model - tiny, base, small, medium, large-v3
   * @param {string} language - auto, en, vi, zh, ja, ko, ...
   */
  async runSTT(jobId, model = 'small', language = 'auto') {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/stt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ model, language })
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi nhận diện STT (${response.status})`);
    }
    return data;
  },

  /**
   * Lấy dữ liệu transcript của Job
   */
  async getTranscript(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/transcript`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Lấy danh sách phụ đề / SpeechChunks đã dịch hoặc gốc của Job
   */
  async getSubtitles(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/subtitles`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Dịch toàn bộ transcript qua Gemini API (Batch Translation)
   * @param {string} jobId
   * @param {string} targetLanguage - vi, en, zh, ja, ko, ...
   * @param {string} sourceLanguage - auto hoặc mã ISO
   * @param {string} apiKey - Gemini API Key (tùy chọn)
   * @param {string} translationStyle - standard_dubbing, movie_review_spoken_vi, natural_commentary
   */
  async translateTranscript(jobId, targetLanguage = 'vi', sourceLanguage = 'auto', apiKey = '', translationStyle = 'standard_dubbing') {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/translate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target_language: targetLanguage,
        source_language: sourceLanguage,
        api_key: apiKey || null,
        translation_style: translationStyle
      })
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi dịch thuật (${response.status})`);
    }
    return data;
  },

  /**
   * Lấy dữ liệu transcript đã dịch của Job
   * @param {string} jobId
   */
  async getTranslatedTranscript(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/translated`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Lấy danh sách giọng đọc AI theo ngôn ngữ
   * @param {string} langCode
   */
  async getVoices(langCode = 'vi') {
    const response = await fetch(`${API_BASE}/tts/voices?language=${encodeURIComponent(langCode)}`);
    if (!response.ok) {
      return { language: langCode, voices: [] };
    }
    return await response.json();
  },

  /**
   * Nghe thử một đoạn audio với giọng đọc đã chọn
   * @param {string} text
   * @param {string} voice
   * @param {string} speedRate
   */
  async previewVoice(text, voice, speedRate = '+0%') {
    const response = await fetch(`${API_BASE}/tts/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        voice,
        speed_rate: speedRate
      })
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi phát âm thanh' }));
      throw new Error(err.detail || `Lỗi nghe thử giọng (${response.status})`);
    }

    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },

  /**
   * Bắt đầu toàn bộ quy trình Lồng tiếng AI (TTS) + Đồng bộ + Mix âm nền + Render Video
   * @param {string} jobId
   * @param {string} voice
   * @param {string} speedRate
   * @param {boolean} keepBackgroundAudio
   * @param {number} backgroundVolume
   * @param {number} voiceVolume
   * @param {boolean} burnSubtitles
   */
  async dubAndRenderVideo(
    jobId,
    voice,
    speedRate = '+15%',
    keepBackgroundAudio = true,
    backgroundVolume = 0.15,
    voiceVolume = 1.0,
    burnSubtitles = false
  ) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/dub-and-render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        voice,
        speed_rate: speedRate,
        keep_background_audio: keepBackgroundAudio,
        background_volume: backgroundVolume,
        voice_volume: voiceVolume,
        burn_subtitles: burnSubtitles
      })
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi lồng tiếng và render video (${response.status})`);
    }
    return data;
  },

  /**
   * Thực thi Unified Pipeline Orchestrator cho Job
   * @param {string} jobId
   * @param {Object} pipelineConfig
   */
  async processPipeline(jobId, pipelineConfig) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(pipelineConfig)
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON từ máy chủ' }));
    if (!response.ok) {
      if (response.status === 409) {
        throw new Error(data.detail || 'Job đang trong tiến trình xử lý.');
      }
      throw new Error(data.detail || `Lỗi xử lý pipeline (${response.status})`);
    }
    return data;
  },

  /**
   * Thử lại Job từ đoạn bị lỗi hoặc chạy lại toàn bộ (Phase 1 / Retry & Resume)
   * @param {string} jobId
   * @param {Object} options - { resume_from_failed: boolean, pipeline_config: Object }
   */
  async retryJob(jobId, options = { resume_from_failed: true }) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/retry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(options)
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi khi thử lại Job (${response.status})`);
    }
    return data;
  },

  /**
   * Lấy danh sách lịch sử tất cả các Job (Job History / Phase 2)
   */
  async getJobs() {
    const response = await fetch(`${API_BASE}/jobs`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Xóa một Job khỏi hệ thống
   * @param {string} jobId
   */
  async deleteJob(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi khi xóa Job' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Upload danh sách video (1 đến 5 video) để tạo Batch (Phase 3 / Batch Upload)
   * @param {File[]} files
   * @param {Function} onProgress
   */
  uploadBatchVideos(files, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      for (const file of files) {
        formData.append('files', file);
      }

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && typeof onProgress === 'function') {
          const pct = Math.round((event.loaded * 100) / event.total);
          onProgress(pct);
        }
      });

      xhr.addEventListener('load', () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.detail || `Lỗi máy chủ: ${xhr.status}`));
          }
        } catch (e) {
          reject(new Error(`Phản hồi không hợp lệ từ máy chủ (${xhr.status})`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Mất kết nối mạng trong quá trình tải lên danh sách video.'));
      });

      xhr.open('POST', `${API_BASE}/batches/upload`, true);
      xhr.send(formData);
    });
  },

  /**
   * Lấy thông tin trạng thái của một Batch
   * @param {string} batchId
   */
  async getBatch(batchId) {
    const response = await fetch(`${API_BASE}/batches/${batchId}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Khởi chạy xử lý toàn bộ hàng đợi Batch theo thứ tự tuần tự (concurrency = 1)
   * @param {string} batchId
   * @param {Object} pipelineConfig
   */
  async processBatch(batchId, pipelineConfig) {
    const response = await fetch(`${API_BASE}/batches/${batchId}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(pipelineConfig)
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi xử lý hàng đợi batch (${response.status})`);
    }
    return data;
  },

  /**
   * Lấy trạng thái cấu hình Gemini API Key từ backend (không bao giờ lộ raw key)
   */
  async getGeminiStatus() {
    const response = await fetch(`${API_BASE}/settings/gemini-status`);
    if (!response.ok) {
      return { configured: false, status: 'NOT_CONFIGURED' };
    }
    return await response.json();
  },

  /**
   * Lưu trữ bảo mật Gemini API Key vào backend (được mã hóa AES-GCM)
   * @param {string} apiKey
   */
  async saveGeminiKey(apiKey) {
    const response = await fetch(`${API_BASE}/settings/gemini-key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ api_key: apiKey })
    });

    const data = await response.json().catch(() => ({ detail: 'Lỗi phản hồi JSON' }));
    if (!response.ok) {
      throw new Error(data.detail || `Lỗi khi lưu API Key (${response.status})`);
    }
    return data;
  },

  /**
   * Xóa Gemini API Key khỏi backend
   */
  async deleteGeminiKey() {
    const response = await fetch(`${API_BASE}/settings/gemini-key`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error('Lỗi khi xóa API Key');
    }
    return await response.json();
  }
};

