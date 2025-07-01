// Validation functions

// export const isValidEmail = (email) => {
//   if (!email) return false;
//   // Basic email regex, consider using a library for robust validation
//   const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
//   return regex.test(String(email).toLowerCase());
// };

// export const isNotEmpty = (value) => {
//   if (value === null || value === undefined) return false;
//   return String(value).trim().length > 0;
// };

// export const hasMinLength = (value, min) => {
//   if (!value) return false;
//   return String(value).length >= min;
// };

// export const isNumber = (value) => {
//   return !isNaN(parseFloat(value)) && isFinite(value);
// };

// Placeholder content:
export function placeholderValidator(value) {
  console.log("Validating value (placeholder):", value);
  return true; // Always valid for placeholder
}
