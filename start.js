const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('\x1b[36m%s\x1b[0m', `
===================================================
      AISA PLATFORM LOCAL DEVELOPMENT LAUNCHER      
===================================================
`);

// 1. Check Docker Desktop
try {
  execSync('docker ps', { stdio: 'ignore' });
} catch (e) {
  console.error('\x1b[31m%s\x1b[0m', '❌ ERROR: Docker is not running!');
  console.error('\x1b[33m%s\x1b[0m', 'Please start "Docker Desktop" first and wait until it is fully active.');
  console.error('\x1b[33m%s\x1b[0m', 'After starting Docker Desktop, run this command again.\n');
  process.exit(1);
}

// 2. Start Infrastructure via Docker Compose
console.log('\x1b[32m%s\x1b[0m', '🔄 Starting Docker infrastructure (PostgreSQL, Redis, Kafka)...');
try {
  execSync('docker compose -f infrastructure/docker/docker-compose.yml up -d', { stdio: 'inherit' });
  console.log('\x1b[32m%s\x1b[0m', '✅ Infrastructure started successfully!\n');
} catch (e) {
  console.error('\x1b[31m%s\x1b[0m', '❌ Failed to start Docker infrastructure.');
  process.exit(1);
}

// 3. Database migrations and generation
console.log('\x1b[32m%s\x1b[0m', '🔄 Initializing Prisma database client & migrations...');
try {
  execSync('pnpm db:generate', { stdio: 'inherit' });
  execSync('pnpm db:migrate:deploy', { stdio: 'inherit' });
  execSync('pnpm db:seed', { stdio: 'inherit' });
  console.log('\x1b[32m%s\x1b[0m', '✅ Database schema prepared and seeded!\n');
} catch (e) {
  console.error('\x1b[31m%s\x1b[0m', '❌ Database initialization failed.');
  process.exit(1);
}

// 4. Start concurrent processes (Turbo dev server and Python AI runtime)
console.log('\x1b[36m%s\x1b[0m', '🚀 Launching AISA Services and Python AI Runtime concurrently...');

function runProcess(command, args, options, prefix, color) {
  const p = spawn(command, args, { ...options, shell: true });

  p.stdout.on('data', (data) => {
    const lines = data.toString().trim().split('\n');
    lines.forEach(line => {
      if (line) console.log(`${color}${prefix}\x1b[0m | ${line}`);
    });
  });

  p.stderr.on('data', (data) => {
    const lines = data.toString().trim().split('\n');
    lines.forEach(line => {
      if (line) console.error(`${color}${prefix} (ERR)\x1b[0m | ${line}`);
    });
  });

  p.on('close', (code) => {
    console.log(`${color}${prefix}\x1b[0m terminated with code ${code}`);
  });

  return p;
}

// Node.js services & frontend (Turborepo)
const nodeProcess = runProcess('pnpm', ['run', 'dev'], { cwd: __dirname }, '[Platform Services]', '\x1b[35m');

// Python AI Runtime
const pythonCmd = process.platform === 'win32' 
  ? path.join(__dirname, 'ai-runtime', '.venv', 'Scripts', 'python.exe')
  : path.join(__dirname, 'ai-runtime', '.venv', 'bin', 'python');

const pythonArgs = ['-m', 'uvicorn', 'api.main:app', '--host', '0.0.0.0', '--port', '8000'];

const pythonProcess = runProcess(pythonCmd, pythonArgs, { cwd: path.join(__dirname, 'ai-runtime'), env: { ...process.env, PYTHONPATH: '.' } }, '[AI Runtime Python]', '\x1b[34m');

// Handle clean shutdown
process.on('SIGINT', () => {
  console.log('\n\x1b[33m%s\x1b[0m', 'Stopping all services...');
  nodeProcess.kill();
  pythonProcess.kill();
  process.exit(0);
});
