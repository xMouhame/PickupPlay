// Make code input numeric + 5 digits max
document.addEventListener("DOMContentLoaded", () => {
  const codeInput = document.getElementById("codeInput");
  if (codeInput) {
    codeInput.addEventListener("input", () => {
      codeInput.value = codeInput.value.replace(/\D/g, "").slice(0, 5);
    });
  }

  // Countdown badge on game page
  const startIsoEl = document.getElementById("gameStartIso");
  const countdownEl = document.getElementById("countdown");
  if (startIsoEl && countdownEl) {
    const start = new Date(startIsoEl.value);

    const tick = () => {
      const now = new Date();
      const diff = start - now;

      if (diff <= 0) {
        countdownEl.textContent = "Game time!";
        return;
      }

      const totalMinutes = Math.floor(diff / 60000);
      const hours = Math.floor(totalMinutes / 60);
      const minutes = totalMinutes % 60;

      countdownEl.textContent = `Starts in ${hours}h ${minutes}m`;
    };

    tick();
    setInterval(tick, 30000);
  }
});

function copyCode() {
  const codeText = document.getElementById("codeText");
  if (!codeText) return;

  const code = codeText.textContent.trim();
  navigator.clipboard.writeText(code).then(() => {
    const btns = document.querySelectorAll("button");
    // Optional tiny feedback: flash the code
    codeText.style.opacity = "0.5";
    setTimeout(() => (codeText.style.opacity = "1"), 250);
  });
}
