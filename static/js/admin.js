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
