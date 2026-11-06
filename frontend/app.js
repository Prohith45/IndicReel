// IndicReel Studio Client Controller (v2.2)
// Scalable Long-Form Video Dubbing Architecture & Async Polling

document.addEventListener("DOMContentLoaded", () => {
  // Elements: Video Input & Dropzone
  const videoDropzone = document.getElementById("videoDropzone");
  const videoFileInput = document.getElementById("videoFileInput");
  const dropzonePrompt = document.getElementById("dropzonePrompt");
  const dropzoneFileSelected = document.getElementById("dropzoneFileSelected");
  const selectedFileName = document.getElementById("selectedFileName");
  const selectedFileSize = document.getElementById("selectedFileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const loadSample45Btn = document.getElementById("loadSample45Btn");
  const loadSampleFullBtn = document.getElementById("loadSampleFullBtn");
  const loadSample16x9Btn = document.getElementById("loadSample16x9Btn");
  const loadSampleStepperBtn = document.getElementById("loadSampleStepperBtn");

  // Elements: Video Trimming
  const detectedDurationBadge = document.getElementById("detectedDurationBadge");
  const trimStartInput = document.getElementById("trimStartInput");
  const trimEndInput = document.getElementById("trimEndInput");
  const presetButtons = document.querySelectorAll(".btn-preset");

  // Elements: Dual Languages
  const dubLangSelect = document.getElementById("dubLangSelect");
  const subLangSelect = document.getElementById("subLangSelect");
  const matchLanguagesBtn = document.getElementById("matchLanguagesBtn");
  const dubVoiceTag = document.getElementById("dubVoiceTag");
  const subLanguageTag = document.getElementById("subLanguageTag");

  // Elements: Voice Mode
  const voiceModeRadios = document.querySelectorAll('input[name="voiceMode"]');
  const voiceModeTabs = document.querySelectorAll(".mode-tab");
  const savedVoiceArea = document.getElementById("savedVoiceArea");
  const savedVoiceSelect = document.getElementById("savedVoiceSelect");
  const deleteVoiceBtn = document.getElementById("deleteVoiceBtn");
  const customVoiceUploadArea = document.getElementById("customVoiceUploadArea");
  const customVoiceInput = document.getElementById("customVoiceInput");
  const customVoiceLabelText = document.getElementById("customVoiceLabelText");
  const saveAsNameInput = document.getElementById("saveAsNameInput");
  const stockVoicePickerArea = document.getElementById("stockVoicePickerArea");
  const stockVoiceSelect = document.getElementById("stockVoiceSelect");

  // Elements: Voice Registration Drawer
  const toggleRegisterVoiceBtn = document.getElementById("toggleRegisterVoiceBtn");
  const registerVoiceForm = document.getElementById("registerVoiceForm");
  const newVoiceNameInput = document.getElementById("newVoiceNameInput");
  const newVoiceFileInput = document.getElementById("newVoiceFileInput");
  const saveNewVoiceBtn = document.getElementById("saveNewVoiceBtn");
  const registerVoiceStatus = document.getElementById("registerVoiceStatus");

  // Elements: Action & Telemetry
  const startDubBtn = document.getElementById("startDubBtn");
  const btnSpinner = document.getElementById("btnSpinner");
  const executionTimer = document.getElementById("executionTimer");
  const cacheHitBadge = document.getElementById("cacheHitBadge");
  const consoleBox = document.getElementById("consoleBox");
  const steps = document.querySelectorAll(".pipeline-step");

  // Elements: Live Progress Bar & Telemetry
  const progressBarContainer = document.getElementById("progressBarContainer");
  const progressStatusLabel = document.getElementById("progressStatusLabel");
  const progressPercentLabel = document.getElementById("progressPercentLabel");
  const progressBarFill = document.getElementById("progressBarFill");
  const chunkBadgeLabel = document.getElementById("chunkBadgeLabel");
  const jobIdLabel = document.getElementById("jobIdLabel");

  // Elements: Studio Player & Viewport Modes
  const modeReelBtn = document.getElementById("modeReelBtn");
  const modeYouTubeBtn = document.getElementById("modeYouTubeBtn");
  const studioPlayerFrame = document.getElementById("studioPlayerFrame");
  const playerPlaceholder = document.getElementById("playerPlaceholder");
  const outputVideoPlayer = document.getElementById("outputVideoPlayer");
  const playerActions = document.getElementById("playerActions");
  const downloadVideoBtn = document.getElementById("downloadVideoBtn");
  const openTabBtn = document.getElementById("openTabBtn");

  // Elements: Transcripts
  const sourceTranscriptText = document.getElementById("sourceTranscriptText");
  const dubbedTranscriptText = document.getElementById("dubbedTranscriptText");
  const subTranscriptText = document.getElementById("subTranscriptText");
  const dubDurationBadge = document.getElementById("dubDurationBadge");
  const copySourceBtn = document.getElementById("copySourceBtn");

  // Elements: Header Status
  const engineStatusText = document.getElementById("engineStatusText");

  let currentVideoFile = null;
  let customVoiceFile = null;
  let detectedDuration = 0;
  let timerInterval = null;
  let timerSeconds = 0;
  let pollInterval = null;
  let lastLoggedMessage = "";

  // Language mapping for labels
  const langNameMap = {
    "te-IN": "Telugu",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "bn-IN": "Bengali",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "or-IN": "Odia",
    "pa-IN": "Punjabi",
    "en-IN": "Indian English"
  };

  // 1. Initial Status Check
  async function checkEngineStatus() {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        if (data.api_configured) {
          engineStatusText.textContent = "Gnani Engine Online";
          logToConsole("Connected to Gnani Voice & Speech API (api.vachana.ai)", "success");
        } else {
          engineStatusText.textContent = "API Key Missing in .env";
          logToConsole("Warning: GNANI_API_KEY is not configured in .env. Running in simulation mode.", "info");
        }
      }
    } catch (err) {
      engineStatusText.textContent = "Server Offline";
      logToConsole("Unable to connect to IndicReel backend.", "error");
    }
  }
  checkEngineStatus();

  // 2. Video Input & Dropzone
  videoDropzone.addEventListener("click", (e) => {
    if (e.target !== removeFileBtn) {
      videoFileInput.click();
    }
  });

  videoFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  videoDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    videoDropzone.classList.add("dragover");
  });

  videoDropzone.addEventListener("dragleave", () => {
    videoDropzone.classList.remove("dragover");
  });

  videoDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    videoDropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  removeFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    currentVideoFile = null;
    videoFileInput.value = "";
    dropzoneFileSelected.classList.add("hidden");
    dropzonePrompt.classList.remove("hidden");
    detectedDurationBadge.textContent = "Duration: --s";
    trimEndInput.placeholder = "End of video";
    trimEndInput.value = "";
    logToConsole("Video file removed.", "info");
  });

  function handleFileSelected(file) {
    if (!file.type.startsWith("video/") && !file.name.match(/\.(mp4|mov|webm)$/i)) {
      alert("Please upload a valid MP4 or MOV video file.");
      return;
    }
    currentVideoFile = file;
    selectedFileName.textContent = file.name;
    selectedFileSize.textContent = formatBytes(file.size);
    dropzonePrompt.classList.add("hidden");
    dropzoneFileSelected.classList.remove("hidden");

    logToConsole(`Video selected: ${file.name} (${formatBytes(file.size)})`, "info");

    // Detect duration and aspect ratio using temporary video element
    const tempVid = document.createElement("video");
    tempVid.preload = "metadata";
    tempVid.onloadedmetadata = () => {
      window.URL.revokeObjectURL(tempVid.src);
      detectedDuration = tempVid.duration;
      detectedDurationBadge.textContent = `Duration: ${detectedDuration.toFixed(1)}s`;
      trimEndInput.placeholder = `${detectedDuration.toFixed(1)}s`;

      const isWide = tempVid.videoWidth > tempVid.videoHeight;
      const aspectLabel = isWide ? "16:9 YouTube Widescreen" : "9:16 Vertical Reel";
      setViewportMode(isWide ? "widescreen" : "reel");

      logToConsole(`Video loaded: ${tempVid.videoWidth}x${tempVid.videoHeight} (${aspectLabel}, ${detectedDuration.toFixed(1)}s)`, "info");
    };
    tempVid.src = URL.createObjectURL(file);
  }

  // Viewport mode switching
  function setViewportMode(mode) {
    if (!studioPlayerFrame) return;
    if (mode === "widescreen") {
      studioPlayerFrame.classList.add("widescreen");
      if (modeYouTubeBtn) modeYouTubeBtn.classList.add("active");
      if (modeReelBtn) modeReelBtn.classList.remove("active");
    } else {
      studioPlayerFrame.classList.remove("widescreen");
      if (modeReelBtn) modeReelBtn.classList.add("active");
      if (modeYouTubeBtn) modeYouTubeBtn.classList.remove("active");
    }
  }

  if (modeReelBtn) {
    modeReelBtn.addEventListener("click", () => setViewportMode("reel"));
  }
  if (modeYouTubeBtn) {
    modeYouTubeBtn.addEventListener("click", () => setViewportMode("widescreen"));
  }

  // 3. Load Sample Videos
  async function loadSampleVideo(sampleFilename, triggerBtn) {
    const originalText = triggerBtn.textContent;
    triggerBtn.textContent = "Loading...";
    triggerBtn.disabled = true;

    try {
      logToConsole(`Fetching sample video: ${sampleFilename}...`, "info");
      const res = await fetch(`/api/sample-reel?name=${sampleFilename}`);
      if (!res.ok) throw new Error("Failed to load sample video from server.");
      const blob = await res.blob();
      const file = new File([blob], sampleFilename, { type: "video/mp4" });
      handleFileSelected(file);
      logToConsole(`Sample video '${sampleFilename}' loaded and ready!`, "success");
    } catch (err) {
      logToConsole(`Error loading sample video: ${err.message}`, "error");
      alert(`Could not load sample video: ${err.message}`);
    } finally {
      triggerBtn.textContent = originalText;
      triggerBtn.disabled = false;
    }
  }

  loadSample45Btn.addEventListener("click", () => {
    setViewportMode("reel");
    loadSampleVideo("test_reel_45s.mp4", loadSample45Btn);
  });

  if (loadSampleFullBtn) {
    loadSampleFullBtn.addEventListener("click", () => {
      setViewportMode("reel");
      loadSampleVideo("sample_reel.mp4", loadSampleFullBtn);
    });
  }

  if (loadSample16x9Btn) {
    loadSample16x9Btn.addEventListener("click", () => {
      setViewportMode("widescreen");
      loadSampleVideo("sample_youtube_16x9_45s.mp4", loadSample16x9Btn);
    });
  }

  if (loadSampleStepperBtn) {
    loadSampleStepperBtn.addEventListener("click", () => {
      setViewportMode("reel");
      loadSampleVideo("video_1.mp4", loadSampleStepperBtn);
    });
  }

  // 4. Video Trimming Presets
  presetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      presetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const start = btn.getAttribute("data-start") || "0";
      const end = btn.getAttribute("data-end") || "";
      trimStartInput.value = start;
      trimEndInput.value = end;
      logToConsole(`Trimming preset applied: ${btn.textContent} (${start}s to ${end || 'End'}s)`, "info");
    });
  });

  // 5. Dual Language Selectors
  dubLangSelect.addEventListener("change", () => {
    const val = dubLangSelect.value;
    const name = langNameMap[val] || val;
    dubVoiceTag.textContent = `Dub Voice (${name})`;
    logToConsole(`Target Dubbing Voice: ${name} (${val})`, "info");
  });

  subLangSelect.addEventListener("change", () => {
    const val = subLangSelect.value;
    const name = langNameMap[val] || val;
    subLanguageTag.textContent = `Subtitles (${name})`;
    logToConsole(`Target Subtitle Language: ${name} (${val})`, "info");
  });

  matchLanguagesBtn.addEventListener("click", () => {
    subLangSelect.value = dubLangSelect.value;
    const val = subLangSelect.value;
    const name = langNameMap[val] || val;
    subLanguageTag.textContent = `Subtitles (${name})`;
    logToConsole(`Matched subtitles to dubbing language: ${name}`, "info");
  });

  // 6. Voice Profiles Manager & Dropdown Population
  async function fetchSavedVoices(autoSelectId = null) {
    if (!savedVoiceSelect) return;
    try {
      const res = await fetch("/api/voices");
      if (!res.ok) throw new Error("Failed to load voices");
      const voices = await res.json();
      savedVoiceSelect.innerHTML = "";
      if (!voices || voices.length === 0) {
        savedVoiceSelect.innerHTML = '<option value="" disabled selected>No saved profiles yet — register one below</option>';
        if (deleteVoiceBtn) deleteVoiceBtn.disabled = true;
      } else {
        if (deleteVoiceBtn) deleteVoiceBtn.disabled = false;
        voices.forEach(v => {
          const opt = document.createElement("option");
          opt.value = v.id;
          opt.textContent = `${v.name} (${v.id.substring(0, 16)}...)`;
          if (autoSelectId && v.id === autoSelectId) {
            opt.selected = true;
          }
          savedVoiceSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.error("Error fetching voices:", err);
      savedVoiceSelect.innerHTML = '<option value="" disabled selected>Error loading saved voices</option>';
    }
  }
  fetchSavedVoices();

  // Voice Mode Tabs switching
  voiceModeTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      voiceModeTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const radio = tab.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        const mode = radio.value;
        if (mode === "saved_voice") {
          if (savedVoiceArea) savedVoiceArea.classList.remove("hidden");
          if (customVoiceUploadArea) customVoiceUploadArea.classList.add("hidden");
          if (stockVoicePickerArea) stockVoicePickerArea.classList.add("hidden");
          fetchSavedVoices();
        } else if (mode === "clone_custom") {
          if (customVoiceUploadArea) customVoiceUploadArea.classList.remove("hidden");
          if (savedVoiceArea) savedVoiceArea.classList.add("hidden");
          if (stockVoicePickerArea) stockVoicePickerArea.classList.add("hidden");
        } else if (mode === "stock_voice") {
          if (stockVoicePickerArea) stockVoicePickerArea.classList.remove("hidden");
          if (customVoiceUploadArea) customVoiceUploadArea.classList.add("hidden");
          if (savedVoiceArea) savedVoiceArea.classList.add("hidden");
        } else {
          // clone_video
          if (customVoiceUploadArea) customVoiceUploadArea.classList.add("hidden");
          if (savedVoiceArea) savedVoiceArea.classList.add("hidden");
          if (stockVoicePickerArea) stockVoicePickerArea.classList.add("hidden");
        }
        logToConsole(`Voice Mode selected: ${mode}`, "info");
      }
    });
  });

  // Delete Voice Profile
  if (deleteVoiceBtn) {
    deleteVoiceBtn.addEventListener("click", async () => {
      const voiceId = savedVoiceSelect.value;
      if (!voiceId) return;
      const voiceName = savedVoiceSelect.options[savedVoiceSelect.selectedIndex]?.textContent || voiceId;
      if (!confirm(`Are you sure you want to delete voice profile '${voiceName}'?`)) {
        return;
      }
      try {
        deleteVoiceBtn.disabled = true;
        const res = await fetch(`/api/voices/${voiceId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Delete failed");
        logToConsole(`[Voice Profile] Deleted profile ${voiceId}`, "info");
        await fetchSavedVoices();
      } catch (err) {
        alert(`Could not delete profile: ${err.message}`);
      } finally {
        deleteVoiceBtn.disabled = false;
      }
    });
  }

  // Toggle Quick Registration Drawer
  if (toggleRegisterVoiceBtn) {
    toggleRegisterVoiceBtn.addEventListener("click", () => {
      registerVoiceForm.classList.toggle("hidden");
      toggleRegisterVoiceBtn.textContent = registerVoiceForm.classList.contains("hidden") ? "+ New Profile" : "Close";
    });
  }

  // Register New Voice Profile Handler
  if (saveNewVoiceBtn) {
    saveNewVoiceBtn.addEventListener("click", async () => {
      const name = newVoiceNameInput.value.trim();
      if (!name) {
        alert("Please enter a name for the voice profile.");
        return;
      }
      if (!newVoiceFileInput.files || newVoiceFileInput.files.length === 0) {
        alert("Please choose a .wav, .mp3, or .mpa audio file.");
        return;
      }
      const audioFile = newVoiceFileInput.files[0];
      saveNewVoiceBtn.disabled = true;
      saveNewVoiceBtn.textContent = "Extracting...";
      registerVoiceStatus.style.display = "block";
      registerVoiceStatus.style.color = "#A5B4FC";
      registerVoiceStatus.textContent = "Extracting 10s slice & computing speaker embedding...";

      const fd = new FormData();
      fd.append("name", name);
      fd.append("audio_file", audioFile);

      try {
        const res = await fetch("/api/voices", { method: "POST", body: fd });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Registration failed" }));
          throw new Error(err.detail || "Server error");
        }
        const data = await res.json();
        registerVoiceStatus.style.color = "#10B981";
        registerVoiceStatus.textContent = `Profile '${data.voice.name}' registered successfully!`;
        logToConsole(`[Voice Profile] Registered '${data.voice.name}' (${data.voice.id}) in voices.json`, "success");
        newVoiceNameInput.value = "";
        newVoiceFileInput.value = "";
        await fetchSavedVoices(data.voice.id);

        // Switch to Saved Voice tab automatically
        const savedRadio = document.querySelector('input[name="voiceMode"][value="saved_voice"]');
        if (savedRadio) {
          const tab = savedRadio.closest(".mode-tab");
          if (tab) tab.click();
        }
      } catch (err) {
        registerVoiceStatus.style.color = "#EF4444";
        registerVoiceStatus.textContent = `Failed: ${err.message}`;
        alert(`Voice registration failed: ${err.message}`);
      } finally {
        saveNewVoiceBtn.disabled = false;
        saveNewVoiceBtn.textContent = "Save Profile";
      }
    });
  }

  // Custom voice file input
  customVoiceUploadArea.addEventListener("click", () => {
    customVoiceInput.click();
  });

  customVoiceInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!file.name.match(/\.(wav|mp3|mpa)$/i)) {
        alert("Please upload a valid .wav, .mp3, or .mpa audio file.");
        return;
      }
      customVoiceFile = file;
      customVoiceLabelText.textContent = `Custom Voice: ${customVoiceFile.name}`;
      logToConsole(`Loaded custom reference voice: ${customVoiceFile.name} (.${file.name.split('.').pop().toLowerCase()})`, "info");
    }
  });

  // 7. Scalable Asynchronous Pipeline Execution
  startDubBtn.addEventListener("click", async () => {
    if (!currentVideoFile) {
      alert("Please upload a video or select a sample reel first.");
      return;
    }

    const selectedVoiceRadio = document.querySelector('input[name="voiceMode"]:checked');
    const voiceMode = selectedVoiceRadio ? selectedVoiceRadio.value : "clone_video";

    if (voiceMode === "saved_voice") {
      if (!savedVoiceSelect || !savedVoiceSelect.value) {
        alert("Please select a saved voice profile, or register a new one below.");
        return;
      }
    }

    if (voiceMode === "clone_custom" && !customVoiceFile) {
      alert("Please choose a custom .wav, .mp3, or .mpa voice reference file, or switch to 'Clone Video Voice'.");
      return;
    }

    const dubLang = dubLangSelect.value;
    const subLang = subLangSelect.value;
    const trimStart = parseFloat(trimStartInput.value) || 0.0;
    const trimEnd = parseFloat(trimEndInput.value) || 0.0;

    // UI State: Running
    setRunningState(true);
    resetPipelineSteps();
    cacheHitBadge.classList.add("hidden");
    startTimer();

    // Show Progress Bar
    if (progressBarContainer) {
      progressBarContainer.classList.remove("hidden");
      progressBarFill.style.width = "5%";
      progressPercentLabel.textContent = "5%";
      progressStatusLabel.textContent = "Uploading video & initializing background job...";
      chunkBadgeLabel.textContent = "";
      jobIdLabel.textContent = "";
    }

    logToConsole(`[Pipeline] Initiating Long-Form Dubbing: Voice=${langNameMap[dubLang]}, Subs=${langNameMap[subLang]}, Mode=${voiceMode}...`, "active");

    const formData = new FormData();
    formData.append("video", currentVideoFile);
    formData.append("dub_lang", dubLang);
    formData.append("sub_lang", subLang);
    formData.append("voice_mode", voiceMode);
    if (trimStart > 0) formData.append("trim_start", trimStart.toString());
    if (trimEnd > 0) formData.append("trim_end", trimEnd.toString());
    if (voiceMode === "saved_voice" && savedVoiceSelect && savedVoiceSelect.value) {
      formData.append("saved_voice_id", savedVoiceSelect.value);
    }
    if (voiceMode === "clone_custom" && customVoiceFile) {
      formData.append("custom_voice", customVoiceFile);
      if (saveAsNameInput && saveAsNameInput.value.trim()) {
        formData.append("save_as_name", saveAsNameInput.value.trim());
      }
    }
    if (voiceMode === "stock_voice" && stockVoiceSelect) {
      formData.append("stock_voice", stockVoiceSelect.value);
    }

    try {
      // 1. Submit job to asynchronous endpoint
      const initResponse = await fetch("/api/dub/long", {
        method: "POST",
        body: formData
      });

      if (!initResponse.ok) {
        const errJson = await initResponse.json().catch(() => ({ detail: initResponse.statusText }));
        throw new Error(errJson.detail || `Server error ${initResponse.status}`);
      }

      const initData = await initResponse.json();
      const jobId = initData.job_id;
      jobIdLabel.textContent = `Job: ${jobId}`;
      logToConsole(`Job registered [${jobId}]. Monitoring telemetry...`, "info");

      // 2. Poll job status
      pollJobStatus(jobId, dubLang, subLang);

    } catch (err) {
      stopTimer();
      setRunningState(false);
      logToConsole(`[Pipeline Error] ${err.message}`, "error");
      alert(`Dubbing initialization failed: ${err.message}`);
    }
  });

  // Polling Controller for Long-Form Jobs
  function pollJobStatus(jobId, dubLang, subLang) {
    clearInterval(pollInterval);
    lastLoggedMessage = "";

    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/dub/status/${jobId}`);
        if (!res.ok) {
          throw new Error(`Status check failed: HTTP ${res.status}`);
        }
        const data = await res.json();

        // Update progress bar & labels
        const prog = Math.min(100, Math.max(5, data.progress || 5));
        progressBarFill.style.width = `${prog}%`;
        progressPercentLabel.textContent = `${prog}%`;

        if (data.message && data.message !== lastLoggedMessage) {
          progressStatusLabel.textContent = data.message;
          logToConsole(data.message, "active");
          lastLoggedMessage = data.message;
        }

        // Update chunk telemetry indicator
        if (data.total_chunks && data.total_chunks > 0) {
          const cur = data.current_chunk || 0;
          const tot = data.total_chunks;
          const pct = Math.round((cur / tot) * 100);
          chunkBadgeLabel.textContent = `Chunk ${cur} of ${tot} (${pct}%)`;
        } else {
          chunkBadgeLabel.textContent = "";
        }

        // Update pipeline step dots
        if (data.step) {
          for (let s = 1; s < data.step; s++) {
            setStepCompleted(s);
          }
          setStepActive(data.step);
        }

        // Handle Job Completion
        if (data.status === "completed") {
          clearInterval(pollInterval);
          stopTimer();
          markAllStepsCompleted();
          setRunningState(false);

          progressBarFill.style.width = "100%";
          progressPercentLabel.textContent = "100%";
          progressStatusLabel.textContent = "Dubbing completed successfully!";

          const result = data.result || {};

          // Cache badge
          cacheHitBadge.classList.remove("hidden");
          if (result.cached) {
            cacheHitBadge.textContent = "● Cache Hit (0 Credits)";
            cacheHitBadge.style.color = "#10B981";
            logToConsole(`[Pipeline] Pipeline finished in ${timerSeconds}s! Reused cached STT & Embeddings.`, "success");
          } else {
            cacheHitBadge.textContent = "● Live Inference Completed";
            cacheHitBadge.style.color = "#C4C0FF";
            logToConsole(`[Pipeline] Fresh inference completed in ${timerSeconds}s across ${result.total_chunks || 1} chunks!`, "success");
          }

          // Populate transcripts
          sourceTranscriptText.textContent = result.original_transcript || "Transcript unavailable.";
          dubbedTranscriptText.textContent = result.translated_dub_text || "Dubbing translation unavailable.";
          subTranscriptText.textContent = result.translated_sub_text || "Subtitle translation unavailable.";
          dubDurationBadge.textContent = `${result.duration || 0}s`;

          // Populate video player & adjust viewport aspect ratio
          if (result.aspect_ratio === "16:9") {
            setViewportMode("widescreen");
          } else {
            setViewportMode("reel");
          }

          outputVideoPlayer.src = result.video_url;
          outputVideoPlayer.classList.remove("hidden");
          playerPlaceholder.classList.add("hidden");
          playerActions.classList.remove("hidden");

          downloadVideoBtn.href = result.video_url;
          downloadVideoBtn.setAttribute("download", `indicreel_${dubLang}_${subLang}.mp4`);
          openTabBtn.href = result.video_url;

          outputVideoPlayer.play().catch(() => {});
        }

        // Handle Job Failure
        if (data.status === "failed") {
          clearInterval(pollInterval);
          stopTimer();
          setRunningState(false);
          const errorMsg = data.error || data.message || "Unknown error";
          progressStatusLabel.textContent = `Failed: ${errorMsg}`;
          progressBarFill.style.background = "#EF4444";
          logToConsole(`[Pipeline Error] ${errorMsg}`, "error");
          alert(`Long-form dubbing failed: ${errorMsg}`);
        }

      } catch (err) {
        logToConsole(`[Telemetry Warning] Status check error: ${err.message}`, "info");
      }
    }, 1200);
  }

  // Helper functions
  function setStepActive(stepNum) {
    const el = document.querySelector(`.pipeline-step[data-step="${stepNum}"]`);
    if (el) {
      el.classList.add("active");
      el.classList.remove("completed");
    }
  }

  function setStepCompleted(stepNum) {
    const el = document.querySelector(`.pipeline-step[data-step="${stepNum}"]`);
    if (el) {
      el.classList.remove("active");
      el.classList.add("completed");
    }
  }

  function resetPipelineSteps() {
    steps.forEach(s => s.classList.remove("active", "completed"));
  }

  function markAllStepsCompleted() {
    steps.forEach(s => {
      s.classList.remove("active");
      s.classList.add("completed");
    });
  }

  function setRunningState(isRunning) {
    startDubBtn.disabled = isRunning;
    if (isRunning) {
      btnSpinner.classList.remove("hidden");
      startDubBtn.querySelector(".btn-content").style.opacity = "0.4";
    } else {
      btnSpinner.classList.add("hidden");
      startDubBtn.querySelector(".btn-content").style.opacity = "1";
    }
  }

  function startTimer() {
    timerSeconds = 0;
    executionTimer.textContent = "00:00";
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      timerSeconds++;
      const m = Math.floor(timerSeconds / 60).toString().padStart(2, "0");
      const s = (timerSeconds % 60).toString().padStart(2, "0");
      executionTimer.textContent = `${m}:${s}`;
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerInterval);
  }

  function logToConsole(message, type = "info") {
    const time = new Date().toLocaleTimeString();
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    line.textContent = `[${time}] ${message}`;
    consoleBox.appendChild(line);
    consoleBox.scrollTop = consoleBox.scrollHeight;
  }

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  // Copy transcript text
  copySourceBtn.addEventListener("click", () => {
    const text = sourceTranscriptText.textContent;
    navigator.clipboard.writeText(text).then(() => {
      copySourceBtn.textContent = "Copied!";
      setTimeout(() => { copySourceBtn.textContent = "Copy"; }, 2000);
    });
  });
});
