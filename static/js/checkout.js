const paymentMethod = document.querySelector("#payment-method");
const installmentField = document.querySelector("#installment-months-field");
const installmentMonths = document.querySelector("#installment-months");
const installmentEstimate = document.querySelector("#installment-estimate");
const checkoutTotal = document.querySelector("[data-checkout-total]");
const tradeInRequested = document.querySelector("#trade-in-requested");
const tradeInDeviceField = document.querySelector("#trade-in-device-field");
const tradeInDevice = document.querySelector("#trade-in-device");
const consultationRequested = document.querySelector("#consultation-requested");
const consultationMessageField = document.querySelector(
  "#consultation-message-field",
);

if (paymentMethod && installmentField && installmentMonths) {
  const installmentPlans = {
    credit_installment: [
      ["3", "3 tháng"],
      ["6", "6 tháng"],
      ["9", "9 tháng"],
      ["12", "12 tháng"],
    ],
    momo_installment: [
      ["6", "6 tháng"],
      ["12", "12 tháng"],
      ["18", "18 tháng"],
      ["24", "24 tháng"],
    ],
  };
  const currencyFormatter = new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 0,
  });

  function updateInstallmentEstimate() {
    const months = Number(installmentMonths.value);
    const total = Number(checkoutTotal?.dataset.checkoutTotal);
    if (!months || !Number.isFinite(total)) {
      installmentEstimate.textContent =
        "Chọn kỳ hạn để xem số tiền ước tính mỗi tháng.";
      return;
    }

    installmentEstimate.textContent =
      `Ước tính ${currencyFormatter.format(Math.ceil(total / months))} ₫/tháng `
      + `trong ${months} tháng; chưa bao gồm lãi suất hoặc phí.`;
  }

  function updateInstallmentOptions() {
    const choices = installmentPlans[paymentMethod.value];
    installmentField.hidden = !choices;
    installmentMonths.required = Boolean(choices);
    installmentEstimate.hidden = !choices;

    if (!choices) {
      installmentMonths.replaceChildren(new Option("Chọn kỳ hạn", ""));
      installmentEstimate.textContent = "";
      return;
    }

    const previousValue = installmentMonths.value;
    installmentMonths.replaceChildren(new Option("Chọn kỳ hạn", ""));
    choices.forEach(([value, label]) => {
      installmentMonths.add(new Option(label, value));
    });
    if (choices.some(([value]) => value === previousValue)) {
      installmentMonths.value = previousValue;
    }
    updateInstallmentEstimate();
  }

  paymentMethod.addEventListener("change", updateInstallmentOptions);
  installmentMonths.addEventListener("change", updateInstallmentEstimate);
  updateInstallmentOptions();
}

if (tradeInRequested && tradeInDeviceField && tradeInDevice) {
  function updateTradeInFields() {
    tradeInDeviceField.hidden = !tradeInRequested.checked;
    tradeInDevice.required = tradeInRequested.checked;
  }

  tradeInRequested.addEventListener("change", updateTradeInFields);
  updateTradeInFields();
}

if (consultationRequested && consultationMessageField) {
  function updateConsultationField() {
    consultationMessageField.hidden = !consultationRequested.checked;
  }

  consultationRequested.addEventListener("change", updateConsultationField);
  updateConsultationField();
}
