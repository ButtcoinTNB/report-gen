/**
 * @fileoverview ESLint rule to detect snake_case property access in TypeScript files
 * @author Insurance Report Generator Team
 */
"use strict";

//------------------------------------------------------------------------------
// Rule Definition
//------------------------------------------------------------------------------

/** @type {import('eslint').Rule.RuleModule} */
module.exports = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Disallow snake_case property access",
      recommended: false,
      url: null, // URL to the documentation page for this rule
    },
    fixable: "code",
    schema: [], // no options
    messages: {
      snakeCaseProperty: "Avoid using snake_case property '{{property}}'. Use camelCase version instead.",
    },
  },

  create(context) {
    /**
     * Checks if a string is in snake_case
     * @param {string} str - The string to check
     * @returns {boolean} True if the string is in snake_case
     */
    function isSnakeCase(str) {
      return /^[a-z]+(_[a-z]+)+$/.test(str);
    }

    /**
     * Converts a snake_case string to camelCase
     * @param {string} str - The snake_case string
     * @returns {string} The camelCase version of the string
     */
    function snakeToCamel(str) {
      return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    }

    return {
      MemberExpression(node) {
        // Skip computed properties like obj['prop']
        if (node.computed) {
          return;
        }

        const property = node.property;
        if (property.type === "Identifier") {
          const propertyName = property.name;
          
          if (isSnakeCase(propertyName)) {
            context.report({
              node: property,
              messageId: "snakeCaseProperty",
              data: {
                property: propertyName,
              },
              fix(fixer) {
                return fixer.replaceText(property, snakeToCamel(propertyName));
              },
            });
          }
        }
      },
    };
  },
}; 