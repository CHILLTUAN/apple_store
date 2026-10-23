const searchOpen = document.querySelector("#search-open");
const searchInput = document.querySelector("#search-input");
const searchOverlay = document.querySelector("#search-overlay");
const searchClose = document.querySelector("#search-close");
const menuOpen = document.querySelector("#menu-open");
const menuOverlay = document.querySelector("#menu-overlay");
const menuClose = document.querySelector("#menu-close");
// querySelector(): tìm phần tử đầu tiên khớp với selector truyền vào.

function showOverlay(overlay) {
  overlay.hidden = false;

  // chờ đến thời điểm vẽ phù hợp rồi kích hoạt hiệu ứng hiện
  requestAnimationFrame(() => {
    overlay.classList.add("is-visible");
  });
}

function hideOverlay(overlay, callback) {
  overlay.classList.remove("is-visible");

  setTimeout(() => {
    overlay.hidden = true;

    if (callback) {
      callback();
    }
  }, 250);
  // chờ 250ms rồi mới đặt hidden = true.
}

function openSearch() {
  showOverlay(searchOverlay);
  searchInput.focus();
  document.body.classList.add("search-open");
}

function closeSearch() {
  if (searchOverlay.hidden) {
    return;
  }
  hideOverlay(searchOverlay, () => {
    document.body.classList.remove("search-open");
  });
}

function openMenu() {
  showOverlay(menuOverlay);
  document.body.classList.add("menu-open");
}

function closeMenu() {
  if (menuOverlay.hidden) {
    return;
  }
  hideOverlay(menuOverlay, () => {
    document.body.classList.remove("menu-open");
  });
}

document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    if (!searchOverlay.hidden) {
      closeSearch();
    }

    if (!menuOverlay.hidden) {
      closeMenu();
    }
  }
});
//* "keydown": sự kiện xảy ra khi người dùng nhấn phím.
//* event.key: cho biết phím nào được nhấn, chẳng hạn "Escape", "Enter" hoặc "a".

document.addEventListener("wheel", closeSearch);

searchOpen.addEventListener("click", openSearch);
//* Khi có sự kiện click xảy ra trên searchOpen, hãy gọi hàm openSearch.

searchOverlay.addEventListener("click", function (event) {
  if (event.target === searchOverlay) {
    closeSearch();
  }
});
// *event.target === searchOverlay: chỉ đóng khi phần tử được bấm chính là lớp phủ.
// *Nếu bấm vào form, ô nhập hoặc nút bên trong, event.target sẽ là phần tử con, nên điều kiện không đúng.
searchClose.addEventListener("click", closeSearch);

menuOpen.addEventListener("click", openMenu);

menuClose.addEventListener("click", closeMenu);
