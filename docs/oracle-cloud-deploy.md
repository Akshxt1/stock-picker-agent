# Oracle Cloud Free Tier Deployment

This guide deploys the Streamlit app on an Oracle Cloud Infrastructure Always Free VM with a stable public IP that can be whitelisted in IIFL.

## 1. Create The VM

1. Sign in to Oracle Cloud Infrastructure.
2. Choose the Mumbai region if it is available for your tenancy.
3. Create an Always Free compute instance:
   - Image: Ubuntu
   - Shape: `VM.Standard.A1.Flex` if available
   - Size: 1 OCPU / 6 GB RAM is enough to start
   - Public IPv4: enabled
   - SSH key: upload or generate one
4. Copy the VM public IPv4 address. Use this as the static IP in the IIFL app portal.

If A1 capacity is unavailable, retry later or use the Always Free AMD micro shape for basic testing. Agent runs may be tight on 1 GB RAM.

## 2. Open Port 8501

In OCI, add an ingress rule to the VM subnet security list or network security group:

```text
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port Range: 8501
```

For a private app, restrict the source CIDR to your own IP instead of `0.0.0.0/0`.

## 3. Prepare Ubuntu

SSH into the VM:

```bash
ssh ubuntu@YOUR_ORACLE_PUBLIC_IP
```

Install system packages:

```bash
sudo apt update
sudo apt install -y git curl build-essential
```

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile
```

Install Python 3.13 through `uv`:

```bash
uv python install 3.13
```

## 4. Clone And Configure The App

Clone the repo:

```bash
git clone https://github.com/Akshxt1/stock-picker-agent.git
cd stock-picker-agent
```

Create `.env` on the VM:

```bash
nano .env
```

Paste the same environment variables you use locally, including:

```env
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
FINNHUB_API_KEY=

IIFL_APP_KEY=
IIFL_APP_SECRET_KEY=
IIFL_REDIRECT_URL=http://YOUR_ORACLE_PUBLIC_IP:8501
IIFL_REGISTERED_IP=YOUR_ORACLE_PUBLIC_IP
```

Install dependencies:

```bash
uv sync
```

Test run:

```bash
uv run streamlit run src/ui/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

Open:

```text
http://YOUR_ORACLE_PUBLIC_IP:8501
```

Stop the test run with `Ctrl+C`.

## 5. Run As A Service

From the repo root on the VM:

```bash
sudo cp deploy/oracle-stock-picker.service /etc/systemd/system/stock-picker.service
sudo systemctl daemon-reload
sudo systemctl enable stock-picker
sudo systemctl start stock-picker
```

Check status:

```bash
sudo systemctl status stock-picker
```

View logs:

```bash
journalctl -u stock-picker -f
```

Restart after code or `.env` changes:

```bash
sudo systemctl restart stock-picker
```

## 6. Update The App Later

```bash
cd ~/stock-picker-agent
git pull
uv sync
sudo systemctl restart stock-picker
```

## Notes

- Keep `.env` only on your local machine and the VM. It is ignored by Git.
- Register the Oracle VM public IPv4 in IIFL.
- If Oracle reclaims an idle Always Free VM, recreate it and update the IP in IIFL.
- Once the app works, consider adding a domain and HTTPS through Caddy or Nginx.
