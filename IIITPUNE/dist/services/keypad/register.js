"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerHandler = registerHandler;
exports.getHandler = getHandler;
const registry = {};
function registerHandler(key, handler) {
    registry[key] = handler;
}
function getHandler(key) {
    return registry[key];
}
