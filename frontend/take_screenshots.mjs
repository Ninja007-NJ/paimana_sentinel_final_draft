import puppeteer from "puppeteer-core";
import path from "path";

const edgePath = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const outputDir = "C:/Users/Niranjan/.gemini/antigravity/brain/9cbe6c83-57da-4b84-bb61-94b5631fc0c6";

async function run() {
  console.log("Launching Edge...");
  const browser = await puppeteer.launch({
    executablePath: edgePath,
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--window-size=1440,1080"]
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1080, deviceScaleFactor: 2 });

  console.log("Navigating to http://localhost:5173/ ...");
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });
  await new Promise(r => setTimeout(r, 1500));

  // 1a. Capture Cyber Stealth Palette
  console.log("Setting palette to cyber and capturing dashboard_cyber.png...");
  await page.evaluate(() => {
    const btn = document.querySelector('button[title*="Cyber Stealth"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({
    path: path.join(outputDir, "dashboard_cyber.png"),
    fullPage: false
  });

  // 1b. Capture Sovereign Gold Palette
  console.log("Setting palette to gold and capturing dashboard_gold.png...");
  await page.evaluate(() => {
    const btn = document.querySelector('button[title*="Sovereign Gold"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({
    path: path.join(outputDir, "dashboard_gold.png"),
    fullPage: false
  });

  // 1c. Capture Deep Cobalt Palette
  console.log("Setting palette to cobalt and capturing dashboard_cobalt.png...");
  await page.evaluate(() => {
    const btn = document.querySelector('button[title*="Deep Cobalt"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({
    path: path.join(outputDir, "dashboard_cobalt.png"),
    fullPage: false
  });

  // Reset back to cyber for remainder
  await page.evaluate(() => {
    const btn = document.querySelector('button[title*="Cyber Stealth"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 500));

  // 1d. Capture Dark Mode default
  console.log("Capturing dashboard_dark.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_dark.png"),
    fullPage: false
  });

  // 2. Open Sentinel AI Copilot and capture
  console.log("Opening Sentinel AI Copilot...");
  await page.click(".sentinel-ai-nav-btn");
  await new Promise(r => setTimeout(r, 600));
  console.log("Capturing dashboard_copilot.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_copilot.png"),
    fullPage: false
  });

  // Click a suggested question to demonstrate active response
  console.log("Clicking suggested question for active chat view...");
  try {
    const chip = await page.$(".sentinel-suggested-item");
    if (chip) {
      await chip.click();
      await new Promise(r => setTimeout(r, 1400));
      console.log("Capturing dashboard_copilot_chat.png...");
      await page.screenshot({
        path: path.join(outputDir, "dashboard_copilot_chat.png"),
        fullPage: false
      });
    }
  } catch (err) {
    console.error("Could not capture chat interaction:", err);
  }

  // Close Copilot
  try {
    await page.click(".btn-close-win");
  } catch (e) {
    await page.evaluate(() => {
      const closeBtn = document.querySelector(".btn-close-win") || document.querySelector(".btn-close-panel");
      if (closeBtn) closeBtn.click();
    });
  }
  await new Promise(r => setTimeout(r, 500));

  // 3. Switch to Light Mode explicitly
  console.log("Switching to Light Mode...");
  await page.evaluate(() => {
    const btn = document.querySelector(".theme-toggle-btn");
    if (btn) {
      btn.click();
    } else {
      document.documentElement.setAttribute("data-theme", "light");
      localStorage.setItem("paimana_theme", "light");
    }
  });
  await new Promise(r => setTimeout(r, 1000));
  
  const currentTheme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  console.log("Current theme after toggle:", currentTheme);

  console.log("Capturing dashboard_light.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_light.png"),
    fullPage: false
  });

  // 4. Capture India Heatmap in dark mode
  console.log("Switching back to Dark mode to capture India Map at bottom...");
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("paimana_theme", "dark");
    const scrollContainer = document.querySelector(".main-scrollable-area");
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  });
  await new Promise(r => setTimeout(r, 800));

  console.log("Capturing dashboard_india_map_dark.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_india_map_dark.png"),
    fullPage: false
  });

  // 5. Also capture full scrolled view of Sector, Alerts & India Map in light mode
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "light");
    localStorage.setItem("paimana_theme", "light");
  });
  await new Promise(r => setTimeout(r, 600));

  console.log("Capturing dashboard_india_map_light.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_india_map_light.png"),
    fullPage: false
  });

  // 6. Test 1-Click Administrative Officer Brief Modal
  console.log("Switching to dark mode and testing 1-Click Brief Modal...");
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("paimana_theme", "dark");
    const scrollContainer = document.querySelector(".main-scrollable-area");
    if (scrollContainer) {
      scrollContainer.scrollTop = 0;
    }
  });
  await new Promise(r => setTimeout(r, 600));

  // Click Brief on first row
  const viewBtns = await page.$$(".early-warning-table button");
  for (const btn of viewBtns) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && (text.includes("Brief") || text.includes("View"))) {
      await btn.click();
      break;
    }
  }
  await new Promise(r => setTimeout(r, 600));

  console.log("Capturing dashboard_brief_modal.png...");
  await page.screenshot({
    path: path.join(outputDir, "dashboard_brief_modal.png"),
    fullPage: false
  });

  // Close modal
  const closeBtn = await page.$(".dossier-close-btn");
  if (closeBtn) await closeBtn.click();
  await new Promise(r => setTimeout(r, 400));

  // 6b. Test Hover Peek Sparkline on Project Name
  console.log("Hovering over project for sparkline peek tooltip...");
  const peekTarget = await page.$(".hover-peek-box");
  if (peekTarget) {
    await peekTarget.hover();
    await page.evaluate(() => {
      const el = document.querySelector(".hover-peek-box");
      if (el) el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    });
    await new Promise(r => setTimeout(r, 600));
    console.log("Capturing dashboard_sparkline_hover.png...");
    await page.screenshot({
      path: path.join(outputDir, "dashboard_sparkline_hover.png"),
      fullPage: false
    });
  }

  // 7. Test State Filter from India Map
  console.log("Testing State Filter from India Map...");
  const mapStateBtn = await page.$(".map-tooltip button");
  if (mapStateBtn) {
    await mapStateBtn.click();
    await new Promise(r => setTimeout(r, 700));
    console.log("Capturing dashboard_state_filter.png...");
    await page.screenshot({
      path: path.join(outputDir, "dashboard_state_filter.png"),
      fullPage: false
    });
  }

  await browser.close();
  console.log("Screenshots captured successfully!");
}

run().catch(console.error);


