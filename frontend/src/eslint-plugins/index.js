/**
 * @fileoverview Custom ESLint rules for the Insurance Report Generator frontend
 * @author Insurance Report Generator Team
 */
"use strict";

//------------------------------------------------------------------------------
// Plugin Definition
//------------------------------------------------------------------------------

/** @type {import('eslint').Plugin} */
module.exports = {
  rules: {
    "no-snake-case-props": require("./no-snake-case-props")
  }
}; 