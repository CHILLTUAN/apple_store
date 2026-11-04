const searchOpen = document.querySelector("#search-open");
const searchInput = document.querySelector("#search-input");
const searchOverlay = document.querySelector("#search-overlay");
const searchClose = document.querySelector("#search-close");
const menuOpen = document.querySelector("#menu-open");
const menuOverlay = document.querySelector("#menu-overlay");
const menuClose = document.querySelector("#menu-close");
// querySelector(): tìm phần tử đầu tiên khớp với selector truyền vào.

document.querySelectorAll(".flash-message").forEach((message) => {
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
// ========================= ========================= base.html ========================= =========================
const links = document.querySelectorAll(".nav-links a");
links.forEach((link) => {
  if (window.location.pathname === link.pathname) {
    link.classList.add("selectedLink");
  } else {
    link.classList.remove("selectedlink");
  }
});

// ========================= ========================= products/list.html ========================= =========================
const capacityButtons = document.querySelectorAll(".option-control button");

capacityButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const price = button.dataset.price;
    const stock = button.dataset.stock;

    const productCard = button.closest(".product-card");
    const productPrice = productCard.querySelector(".product-price");
    productPrice.textContent = Number(price).toLocaleString("vi-VN") + " ₫";
    const stockDisplay = productCard.querySelector("[data-product-stock]");
    if (stockDisplay) {
      stockDisplay.textContent =
        Number(stock) > 0 ? `Còn ${stock} sản phẩm` : "Hết hàng";
    }
    const detailLink = productCard.querySelector(".product-detail-link");
    if (detailLink) {
      detailLink.href = button.dataset.detailUrl;
    }

    const buttonsInProductCard = productCard.querySelectorAll(
      ".option-control button",
    );

    buttonsInProductCard.forEach((button) => {
      button.classList.remove("selected");
    });

    button.classList.add("selected");
  });
});

const cartQuantityInputs = document.querySelectorAll(
  ".cart-quantity-form input[name='quantity'][data-unit-price]",
);

if (cartQuantityInputs.length) {
  const cartTotal = document.querySelector(".cart-total span");
  const cartItems = document.querySelectorAll(".cart-item");
  const currencyFormatter = new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 0,
  });

  function formatCartPrice(amount) {
    return `${currencyFormatter.format(Math.round(amount))} ₫`;
  }

  function updateCartTotals() {
    let total = 0;
    cartItems.forEach((item) => {
      const input = item.querySelector(
        ".cart-quantity-form input[name='quantity'][data-unit-price]",
      );
      const lineTotalDisplay = item.querySelector(".cart-line-total");
      let lineTotal = Number(lineTotalDisplay.dataset.lineTotal);

      if (input) {
        const quantity = Number(input.value);
        const unitPrice = Number(input.dataset.unitPrice);
        const maximum = Number(input.max);
        if (
          Number.isInteger(quantity)
          && quantity >= 1
          && quantity <= maximum
          && Number.isFinite(unitPrice)
        ) {
          lineTotal = unitPrice * quantity;
          lineTotalDisplay.dataset.lineTotal = String(lineTotal);
          lineTotalDisplay.textContent = formatCartPrice(lineTotal);
        }
      }

      total += lineTotal;
    });

    if (cartTotal) {
      cartTotal.textContent = formatCartPrice(total);
    }
  }

  cartQuantityInputs.forEach((input) => {
    input.addEventListener("input", updateCartTotals);
    input.addEventListener("change", () => {
      if (!input.form || !input.reportValidity()) {
        return;
      }

      const status = input.form.querySelector(".cart-quantity-status");
      if (status) {
        status.textContent = "Đang cập nhật…";
      }
      input.form.requestSubmit();
    });
  });
}
