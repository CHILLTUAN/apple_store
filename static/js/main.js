// document: đại diện cho tài liệu HTML hiện tại.
// querySelector(): tìm phần tử đầu tiên khớp với selector truyền vào.
const searchOpen = document.querySelector("#search-open");
const searchInput = document.querySelector("#search-input");
const searchOverlay = document.querySelector("#search-overlay");
const searchClose = document.querySelector("#search-close");

function openSearch() {
  searchOverlay.hidden = false;

  searchInput.focus();
}

function closeSearch() {
  searchOverlay.hidden = true;
}

searchOpen.addEventListener("click", openSearch);
// Khi có sự kiện click xảy ra trên searchOpen, hãy gọi hàm openSearch.

searchOverlay.addEventListener("click", function (event) {
  if (event.target === searchOverlay) {
    closeSearch();
  }
  // event.target === searchOverlay: chỉ đóng khi phần tử được bấm chính là lớp phủ. Nếu bấm vào form, ô nhập hoặc nút bên trong, event.target sẽ là phần tử con, nên điều kiện không đúng.
});

searchClose.addEventListener("click", closeSearch);

// document: lắng nghe sự kiện trên toàn tài liệu.

// "keydown": sự kiện xảy ra khi người dùng nhấn phím.

// event.key: cho biết phím nào được nhấn, chẳng hạn "Escape", "Enter" hoặc "a".

document.addEventListener("keydown", function (event) {
  console.log("Phím vừa nhấn:", event.key);

  if (event.key === "Escape") {
    closeSearch();
  }
});

document.addEventListener("wheel", closeSearch);
