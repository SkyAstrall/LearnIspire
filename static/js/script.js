/**
 * LearnIspire Main JavaScript File
 */

document.addEventListener("DOMContentLoaded", function () {
  // Initialize tooltips
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]'
  );
  const tooltipList = [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
  );

  // Initialize popovers
  const popoverTriggerList = document.querySelectorAll(
    '[data-bs-toggle="popover"]'
  );
  const popoverList = [...popoverTriggerList].map(
    (popoverTriggerEl) => new bootstrap.Popover(popoverTriggerEl)
  );

  // Auto-hide alerts after 5 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
    alerts.forEach(function (alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);

  // Dynamic form controls
  setupDynamicFormControls();

  // Initialize date pickers
  initializeDatePickers();

  // Table sorting functionality
  initializeTableSorting();

  // Availability slots management
  initializeAvailabilitySlots();
});

/**
 * Sets up dynamic form controls like add/remove fields
 */
function setupDynamicFormControls() {
  // Add Availability Slot
  const addSlotBtn = document.getElementById("add-availability-slot");
  if (addSlotBtn) {
    addSlotBtn.addEventListener("click", function () {
      const slotContainer = document.getElementById("availability-slots");
      const slotTemplate = document.getElementById("slot-template");
      if (slotContainer && slotTemplate) {
        const newSlot = slotTemplate.content.cloneNode(true);
        const slotCount = slotContainer.children.length;

        // Update IDs and names
        const inputs = newSlot.querySelectorAll("select, input");
        inputs.forEach((input) => {
          const name = input.getAttribute("name");
          if (name) {
            input.setAttribute("name", name.replace("__index__", slotCount));
          }
          const id = input.getAttribute("id");
          if (id) {
            input.setAttribute("id", id.replace("__index__", slotCount));
          }
        });

        // Add remove button functionality
        const removeBtn = newSlot.querySelector(".remove-slot");
        if (removeBtn) {
          removeBtn.addEventListener("click", function () {
            this.closest(".availability-slot").remove();
          });
        }

        slotContainer.appendChild(newSlot);
      }
    });
  }

  // Remove Availability Slot
  const removeSlotBtns = document.querySelectorAll(".remove-slot");
  removeSlotBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      this.closest(".availability-slot").remove();
    });
  });
}

/**
 * Initializes date picker inputs
 */
function initializeDatePickers() {
  // Set min date for date inputs to today
  const dateInputs = document.querySelectorAll('input[type="date"]');
  dateInputs.forEach((input) => {
    if (input.getAttribute("min") === "today") {
      const today = new Date().toISOString().split("T")[0];
      input.setAttribute("min", today);
    }
  });
}

/**
 * Initializes table sorting functionality
 */
function initializeTableSorting() {
  const sortableTables = document.querySelectorAll(".table-sortable");
  sortableTables.forEach((table) => {
    const headers = table.querySelectorAll("th[data-sort]");
    headers.forEach((header) => {
      header.addEventListener("click", function () {
        const sortKey = this.dataset.sort;
        const sortOrder = this.dataset.sortOrder === "asc" ? "desc" : "asc";

        // Update sort indicators
        headers.forEach((h) => {
          h.dataset.sortOrder = "";
          h.querySelector(".sort-indicator")?.remove();
        });

        this.dataset.sortOrder = sortOrder;
        const indicator = document.createElement("span");
        indicator.className = "sort-indicator ms-1";
        indicator.innerHTML = sortOrder === "asc" ? "▲" : "▼";
        this.appendChild(indicator);

        // Sort the table
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));

        rows.sort((a, b) => {
          const aValue =
            a.querySelector(`td[data-${sortKey}]`)?.dataset[sortKey] ||
            a
              .querySelector(
                `td:nth-child(${Array.from(headers).indexOf(this) + 1})`
              )
              ?.textContent.trim();
          const bValue =
            b.querySelector(`td[data-${sortKey}]`)?.dataset[sortKey] ||
            b
              .querySelector(
                `td:nth-child(${Array.from(headers).indexOf(this) + 1})`
              )
              ?.textContent.trim();

          if (sortOrder === "asc") {
            return aValue.localeCompare(bValue, undefined, { numeric: true });
          } else {
            return bValue.localeCompare(aValue, undefined, { numeric: true });
          }
        });

        // Update the DOM
        rows.forEach((row) => tbody.appendChild(row));
      });
    });
  });
}

/**
 * Initializes availability slots management
 */
function initializeAvailabilitySlots() {
  // Conflict checking
  const availabilityForm = document.getElementById("availability-form");
  if (availabilityForm) {
    availabilityForm.addEventListener("submit", function (e) {
      const slots = document.querySelectorAll(".availability-slot");

      // Check if at least 3 slots are provided
      if (slots.length < 3) {
        e.preventDefault();
        alert("Please provide at least 3 availability slots per week.");
        return;
      }

      // Check for conflicts
      const slotData = [];
      slots.forEach((slot) => {
        const day = slot.querySelector('select[name*="day"]').value;
        const startTime = slot.querySelector('input[name*="start_time"]').value;
        const endTime = slot.querySelector('input[name*="end_time"]').value;

        if (startTime >= endTime) {
          e.preventDefault();
          alert("Start time must be before end time for all slots.");
          return;
        }

        slotData.push({ day, startTime, endTime });
      });

      // Check for overlapping slots
      for (let i = 0; i < slotData.length; i++) {
        for (let j = i + 1; j < slotData.length; j++) {
          if (slotData[i].day === slotData[j].day) {
            // Check if slots overlap
            if (
              (slotData[i].startTime >= slotData[j].startTime &&
                slotData[i].startTime < slotData[j].endTime) ||
              (slotData[i].endTime > slotData[j].startTime &&
                slotData[i].endTime <= slotData[j].endTime) ||
              (slotData[i].startTime <= slotData[j].startTime &&
                slotData[i].endTime >= slotData[j].endTime)
            ) {
              e.preventDefault();
              alert(
                "You have overlapping availability slots. Please fix them and try again."
              );
              return;
            }
          }
        }
      }
    });
  }
}

/**
 * Class timer countdown function
 * @param {string} startTimeStr - Start time ISO string
 * @param {string} endTimeStr - End time ISO string
 * @param {string} elementId - ID of element to update
 */
function initClassTimer(startTimeStr, endTimeStr, elementId) {
  const startTime = new Date(startTimeStr);
  const endTime = new Date(endTimeStr);
  const timerElement = document.getElementById(elementId);

  if (!timerElement) return;

  function updateTimer() {
    const now = new Date();
    let timerText = "";
    let timerClass = "";

    if (now < startTime) {
      // Class hasn't started
      const diff = Math.floor((startTime - now) / 1000);
      const hours = Math.floor(diff / 3600);
      const minutes = Math.floor((diff % 3600) / 60);
      const seconds = diff % 60;

      timerText = `Starts in ${hours.toString().padStart(2, "0")}:${minutes
        .toString()
        .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
      timerClass = "text-primary";
    } else if (now > endTime) {
      // Class has ended
      timerText = "Class Ended";
      timerClass = "text-danger";
    } else {
      // Class is ongoing
      const diff = Math.floor((endTime - now) / 1000);
      const hours = Math.floor(diff / 3600);
      const minutes = Math.floor((diff % 3600) / 60);
      const seconds = diff % 60;

      timerText = `Ends in ${hours.toString().padStart(2, "0")}:${minutes
        .toString()
        .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
      timerClass = "text-success";
    }

    timerElement.textContent = timerText;
    timerElement.className = timerClass;
  }

  // Update immediately and then every second
  updateTimer();
  return setInterval(updateTimer, 1000);
}
