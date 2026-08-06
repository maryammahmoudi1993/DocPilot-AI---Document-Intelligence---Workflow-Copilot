import '@testing-library/jest-dom';

// jsdom doesn't implement the Pointer Events capture API or
// scrollIntoView. Radix UI primitives (Toast, Select, Dialog swipe/drag
// handling) call these unconditionally, so every test using them throws
// without this polyfill — a standard, widely-documented Radix+jsdom
// workaround, not something specific to this project's components.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
