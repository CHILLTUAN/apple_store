// document: đại diện cho tài liệu HTML hiện tại.
// querySelector(): tìm phần tử đầu tiên khớp với selector truyền vào.
const searchOpen = document.querySelector("#search-open");
const searchInput = document.querySelector("#search-input");
const searchOverlay = document.querySelector("#search-overlay");
const searchClose = document.querySelector("#search-close");
const menuOpen = document.querySelector("#menu-open");
const menuOverlay = document.querySelector("#menu-overlay");
const menuClose = document.querySelector("#menu-close");

// SEARCH OVERLAY
function openSearch() {
  searchOverlay.hidden = false;
  searchInput.focus();
  document.body.classList.add("search-open");
}

function closeSearch() {
  searchOverlay.hidden = true;
  document.body.classList.remove("search-open");
}

searchOpen.addEventListener("click", openSearch);
// Khi có sự kiện click xảy ra trên searchOpen, hãy gọi hàm openSearch.

searchOverlay.addEventListener("click", function (event) {
  if (event.target === searchOverlay) {
    closeSearch();
  }
});
// event.target === searchOverlay: chỉ đóng khi phần tử được bấm chính là lớp phủ.
// Nếu bấm vào form, ô nhập hoặc nút bên trong, event.target sẽ là phần tử con, nên điều kiện không đúng.

searchClose.addEventListener("click", closeSearch);

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
// "keydown": sự kiện xảy ra khi người dùng nhấn phím.
// event.key: cho biết phím nào được nhấn, chẳng hạn "Escape", "Enter" hoặc "a".

document.addEventListener("wheel", closeSearch);

// MENU OVERLAY
function openMenu() {
  menuOverlay.hidden = false;
  document.body.classList.add("menu-open");
}
menuOpen.addEventListener("click", openMenu);

function closeMenu() {
  menuOverlay.hidden = true;
  document.body.classList.remove("menu-open");
}
menuClose.addEventListener("click", closeMenu);
