document.querySelectorAll(".admin-flash").forEach((message) => {
  setTimeout(() => {
    message.classList.add("is-dismissing");
    setTimeout(() => {
      const container = message.parentElement;
      message.remove();
      if (container && container.childElementCount === 0) {
        container.remove();
      }
    }, 300);
  }, 5000);
});

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const inputId = button.dataset.passwordToggle;
    const passwordInput = inputId ? document.getElementById(inputId) : null;
    if (!(passwordInput instanceof HTMLInputElement)) {
      return;
    }

    const revealPassword = passwordInput.type === "password";
    passwordInput.type = revealPassword ? "text" : "password";
    button.setAttribute("aria-pressed", String(revealPassword));
    button.setAttribute(
      "aria-label",
      revealPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu",
    );
  });
});
