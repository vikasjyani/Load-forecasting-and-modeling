// Data formatting utilities

// export const formatDate = (dateString, options = {}) => {
//   const defaultOptions = {
//     year: 'numeric', month: 'long', day: 'numeric',
//     hour: '2-digit', minute: '2-digit',
//     ...options,
//   };
//   try {
//     return new Intl.DateTimeFormat('en-US', defaultOptions).format(new Date(dateString));
//   } catch (error) {
//     console.error("Error formatting date:", dateString, error);
//     return "Invalid Date";
//   }
// };

// export const formatCurrency = (amount, currency = 'USD', options = {}) => {
//   const defaultOptions = {
//     style: 'currency',
//     currency: currency,
//     ...options,
//   };
//   try {
//     return new Intl.NumberFormat('en-US', defaultOptions).format(amount);
//   } catch (error) {
//     console.error("Error formatting currency:", amount, error);
//     return "Invalid Amount";
//   }
// };

// export const capitalizeFirstLetter = (string) => {
//   if (!string) return '';
//   return string.charAt(0).toUpperCase() + string.slice(1);
// };

// Placeholder content:
export function placeholderFormatter(value) {
  console.log("Formatting value (placeholder):", value);
  return `Formatted: ${value}`;
}
