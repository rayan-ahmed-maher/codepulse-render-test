import express from "express";

export function runLocal(projectPath) {
  const app = express();

  app.use(express.static(projectPath));

  const PORT = 3000;

  app.listen(PORT, () => {
    console.log("Running on http://localhost:3000");
  });

  return "http://localhost:3000";
}