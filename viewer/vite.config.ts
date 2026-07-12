import { defineConfig, type Plugin } from "vite";
import fs from "node:fs";
import path from "node:path";

// 開発時のみ、コンバーターの output/ ディレクトリを /data/* として配信する。
// PMTiles は HTTP Range リクエストで部分取得されるため Range 対応が必須。
// public/ に置くとビルド時に dist へコピーされてしまう（650MB）ので middleware で配信する。
function serveConverterOutput(): Plugin {
  const dataDir = path.resolve(__dirname, "../output");
  return {
    name: "serve-converter-output",
    configureServer(server) {
      server.middlewares.use("/data", (req, res, next) => {
        const urlPath = decodeURIComponent((req.url ?? "/").split("?")[0]);
        const filePath = path.normalize(path.join(dataDir, urlPath));
        if (!filePath.startsWith(dataDir)) return next();
        let stat: fs.Stats;
        try {
          stat = fs.statSync(filePath);
        } catch {
          return next();
        }
        if (!stat.isFile()) return next();

        res.setHeader("Accept-Ranges", "bytes");
        res.setHeader("Content-Type", "application/octet-stream");

        const range = req.headers.range;
        const m = range ? /^bytes=(\d*)-(\d*)$/.exec(range) : null;
        if (m && (m[1] !== "" || m[2] !== "")) {
          let start: number;
          let end: number;
          if (m[1] === "") {
            // suffix range: bytes=-N（末尾Nバイト）
            start = Math.max(0, stat.size - Number(m[2]));
            end = stat.size - 1;
          } else {
            start = Number(m[1]);
            end = m[2] === "" ? stat.size - 1 : Math.min(Number(m[2]), stat.size - 1);
          }
          if (start > end || start >= stat.size) {
            res.writeHead(416, { "Content-Range": `bytes */${stat.size}` });
            return res.end();
          }
          res.writeHead(206, {
            "Content-Range": `bytes ${start}-${end}/${stat.size}`,
            "Content-Length": end - start + 1,
          });
          fs.createReadStream(filePath, { start, end }).pipe(res);
        } else {
          res.writeHead(200, { "Content-Length": stat.size });
          fs.createReadStream(filePath).pipe(res);
        }
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [serveConverterOutput()],
  server: {
    // WSL2 から /mnt/c 上のファイルを扱う場合 inotify が効かないため、
    // ポーリングでファイル変更を検知する
    watch: { usePolling: true, interval: 1000 },
  },
});
