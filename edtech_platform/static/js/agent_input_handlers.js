/**
 * Generic Agent Input Handlers — ExcellStudy
 * Manages form serialization, validation schemas, file uploads, and invoke calls.
 */

function initAgentInputForm() {
  const form = document.getElementById("agent-input-form");
  if (!form) return;

  if (form.dataset.inputType === "image_upload") {
    initImageUploadHandler(form);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const inputData = serializeFormToInputPayload(form);
    await submitAgentInvoke(inputData);
  });
}

function serializeFormToInputPayload(form) {
  const inputType = form.dataset.inputType;
  
  if (inputType === "multiple_choice") {
    const selected = form.querySelector('input[name="selected_index"]:checked');
    return {
      selected_index: selected ? parseInt(selected.value, 10) : 0
    };
  }
  
  if (inputType === "number") {
    const val = form.querySelector('input[name="value"]').value;
    return {
      value: parseFloat(val)
    };
  }

  if (inputType === "image_upload") {
    const url = form.querySelector('input[name="image_url"]').value;
    return {
      image_url: url
    };
  }

  // default for text_with_units and free_text
  const val = form.querySelector('[name="value"]').value;
  return {
    value: val
  };
}

function initImageUploadHandler(form) {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const statusContainer = document.getElementById("upload-status-container");
  const imgPreview = document.getElementById("image-preview");
  const filenameText = document.getElementById("upload-filename");
  const progressText = document.getElementById("upload-progress-text");
  const removeBtn = document.getElementById("remove-file-btn");
  const submitBtn = document.getElementById("image-submit-btn");
  const hiddenUrlInput = document.getElementById("hidden-image-url");

  // Drag & drop listeners
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--primary)";
    dropZone.style.background = "rgba(83,74,183,0.05)";
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "var(--primary)/30";
    dropZone.style.background = "#F8F7FF";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--primary)/30";
    dropZone.style.background = "#F8F7FF";
    
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  removeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    resetUpload();
  });

  async function handleFileUpload(file) {
    if (!file.type.startsWith("image/")) {
      alert("Invalid file type. Only images are allowed.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert("File too large. Max size is 10MB.");
      return;
    }

    // Show initial preview locally
    const reader = new FileReader();
    reader.onload = (e) => {
      imgPreview.src = e.target.result;
    };
    reader.readAsDataURL(file);

    filenameText.textContent = file.name;
    progressText.textContent = "Uploading image...";
    statusContainer.classList.remove("hidden");
    dropZone.classList.add("hidden");

    // Perform actual upload
    const formData = new FormData();
    formData.append("file", file);

    try {
      const csrfElement = form.querySelector('[name=csrfmiddlewaretoken]');
      const csrfToken = csrfElement ? csrfElement.value : "";

      const res = await fetch("/learner/upload-image/", {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken
        },
        body: formData
      });

      const responseData = await res.json();
      if (res.ok && responseData.status === "success") {
        const uploadedUrl = responseData.data.image_url;
        hiddenUrlInput.value = uploadedUrl;
        progressText.textContent = "Upload complete!";
        progressText.style.color = "var(--accent)";
        submitBtn.disabled = false;
      } else {
        throw new Error(responseData.message || "Upload failed");
      }
    } catch (err) {
      console.error(err);
      progressText.textContent = "Upload failed. Try again.";
      progressText.style.color = "var(--error)";
      submitBtn.disabled = true;
    }
  }

  function resetUpload() {
    fileInput.value = "";
    hiddenUrlInput.value = "";
    imgPreview.src = "#";
    statusContainer.classList.add("hidden");
    dropZone.classList.remove("hidden");
    submitBtn.disabled = true;
    progressText.style.color = "inherit";
  }
}

async function submitAgentInvoke(inputPayload) {
  showLoadingState();
  hideErrorBanner();
  
  const responseContainer = document.getElementById("agent-response");
  const invokeUrl = responseContainer.dataset.invokeUrl;

  try {
    const res = await fetch(invokeUrl, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({
        input: inputPayload,
        context: { learner_id: window.LEARNER_ID }
      }),
    });
    
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.message || `Server returned ${res.status}`);
    }

    const envelope = await res.json();
    hideLoadingState();

    if (envelope.status === "error") {
      showErrorBanner(envelope.message || "An error occurred.", envelope.error_code || "AGENT_ERROR");
      return;
    }

    // Render content blocks inside envelope.data.content
    const content = envelope.data ? envelope.data.content : null;
    renderAgentResponse(content);
  } catch (err) {
    hideLoadingState();
    showErrorBanner(err.message || "Something went wrong. Please try again.", "NETWORK_ERROR");
  }
}

function showLoadingState() {
  document.getElementById("invoke-loading").style.display = "block";
  document.getElementById("agent-response").innerHTML = "";
}

function hideLoadingState() {
  document.getElementById("invoke-loading").style.display = "none";
}

function showErrorBanner(message, code) {
  document.getElementById("error-title").textContent = `Error [${code}]`;
  document.getElementById("error-message").textContent = message;
  document.getElementById("invoke-error").style.display = "flex";
}

function hideErrorBanner() {
  document.getElementById("invoke-error").style.display = "none";
}

document.addEventListener("DOMContentLoaded", initAgentInputForm);
