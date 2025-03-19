// cypress.config.ts - Cypress configuration file
import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "https://report-gen-liard.vercel.app", // Update if needed
    setupNodeEvents(on, config) {
      require("@cypress/webpack-preprocessor")({
        webpackOptions: {
          resolve: {
            extensions: [".ts", ".tsx", ".js"],
          },
          module: {
            rules: [
              {
                test: /\.tsx?$/,
                loader: "ts-loader",
                options: { transpileOnly: true },
              },
            ],
          },
        },
      });
    },
  },
});