# Monitor de Notas Técnicas da NF-e → Telegram

Bot em Python que acompanha a página de Notas Técnicas do Portal da NF-e, quando aparece uma publicação nova, envia para um grupo (ou tópico específico) do Telegram uma mensagem com o título, o link e o arquivo anexado (PDF/ZIP).

Página monitorada:
`https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=04BIflQt1aY=`

---

## Sumário

1. [Requisitos](#1-requisitos)
2. [Instalação](#2-instalação)
3. [Criar o bot no Telegram](#3-criar-o-bot-no-telegram)
4. [Descobrir o ID do grupo](#4-descobrir-o-id-do-grupo)
5. [Descobrir o ID do tópico (opcional)](#5-descobrir-o-id-do-tópico-opcional)
6. [Configurar as variáveis de ambiente](#6-configurar-as-variáveis-de-ambiente)
7. [Testar](#7-testar)
8. [Rodar o bot](#8-rodar-o-bot)
9. [Deixar rodando sozinho](#9-deixar-rodando-sozinho)
10. [Como o bot funciona](#10-como-o-bot-funciona)
11. [Solução de problemas](#11-solução-de-problemas)

---

## 1. Requisitos

- Python 3.8 ou superior (baixe em https://www.python.org/downloads/; no Windows, marque **"Add Python to PATH"** na instalação)
- Uma conta no Telegram
- Computador ou servidor que fique ligado, caso queira o monitoramento contínuo (de preferência com IP brasileiro, pois alguns sites do governo bloqueiam IPs de fora do país)

## 2. Instalação

Coloque o arquivo `monitor_nt.py` em uma pasta, abra o terminal nela e instale as dependências:

```bash
pip install requests beautifulsoup4
```

Se `pip` não for reconhecido, tente:

```bash
python -m pip install requests beautifulsoup4
# ou, no Windows:
py -m pip install requests beautifulsoup4
```

Se aparecer o erro `externally-managed-environment` (Linux/Mac), use um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install requests beautifulsoup4
```

Conferir a instalação:

```bash
python -c "import requests, bs4; print('ok')"
```

## 3. Criar o bot no Telegram

1. No Telegram, abra uma conversa com **@BotFather**.
2. Envie `/newbot` e siga as instruções (nome e username terminado em `bot`).
3. Guarde o **token** que ele devolver (formato `123456789:ABC-DEF...`). **Não compartilhe esse token.**
4. Adicione o bot ao grupo onde as notificações serão enviadas.

## 4. Descobrir o ID do grupo

1. No grupo, envie uma mensagem mencionando o bot, por exemplo: `@nome_do_seu_bot oi` (bots em grupo só enxergam comandos e menções).
2. Abra no navegador, trocando pelo seu token:

   ```
   https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
   ```

3. Procure por `"chat":{"id":...}`. O ID do grupo é **negativo**, por exemplo `-1001234567890`. Copie incluindo o sinal de menos.

Se a resposta vier vazia (`"result":[]`), confirme que a mensagem foi enviada no grupo com a menção ao bot e atualize a página. Se persistir, limpe um possível webhook abrindo:

```
https://api.telegram.org/bot<SEU_TOKEN>/deleteWebhook
```

Alternativa: adicione temporariamente o **@RawDataBot** ao grupo; ele mostra o ID. Depois remova-o.

## 5. Descobrir o ID do tópico (opcional)

Use apenas se o grupo tiver **tópicos** ativados e você quiser enviar para um específico. Sem isso, as mensagens vão para o tópico "Geral".

- Abra o tópico desejado, toque em qualquer mensagem e escolha **Copiar link**.
- O link terá o formato `https://t.me/c/1234567890/5/12`. O número do meio (`5`) é o **ID do tópico**.

Também é possível enviar uma mensagem dentro do tópico mencionando o bot e procurar `"message_thread_id"` no `getUpdates`.

## 6. Configurar as variáveis de ambiente

O script lê a configuração de variáveis de ambiente:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `TELEGRAM_TOKEN` | Sim | Token fornecido pelo BotFather |
| `TELEGRAM_CHAT_ID` | Sim | ID do grupo (ex.: `-1001234567890`) |
| `TELEGRAM_THREAD_ID` | Não | ID do tópico dentro do grupo (ex.: `5`) |

**Linux / Mac:**

```bash
export TELEGRAM_TOKEN="seu_token"
export TELEGRAM_CHAT_ID="-1001234567890"
export TELEGRAM_THREAD_ID="5"
```

**Windows (cmd):**

```
set TELEGRAM_TOKEN=seu_token
set TELEGRAM_CHAT_ID=-1001234567890
set TELEGRAM_THREAD_ID=5
```

**Windows (PowerShell):**

```powershell
$env:TELEGRAM_TOKEN="seu_token"
$env:TELEGRAM_CHAT_ID="-1001234567890"
$env:TELEGRAM_THREAD_ID="5"
```

Essas variáveis valem apenas para a janela de terminal atual. Para tornar permanente, veja a seção 9.

### Ajustes opcionais no topo do `monitor_nt.py`

| Variável | Padrão | Função |
|---|---|---|
| `INTERVALO` | `15 * 60` | Segundos entre cada checagem |
| `VERIFICAR_SSL` | `True` | Mude para `False` se der erro de certificado no site da Fazenda (menos seguro) |
| `ESTADO` | `estado_nt.json` | Arquivo onde ficam os itens já vistos |

Recomendação: para o arquivo de estado ficar sempre ao lado do script, independentemente de onde você rode o comando, use:

```python
ESTADO = Path(__file__).resolve().parent / "estado_nt.json"
```

## 7. Testar

**a) Testar se o token e o ID estão certos.** Abra no navegador:

```
https://api.telegram.org/bot<SEU_TOKEN>/sendMessage?chat_id=<ID_DO_GRUPO>&text=teste
```

Se "teste" chegar no grupo, está tudo certo. (Para testar o tópico, acrescente `&message_thread_id=<ID_DO_TOPICO>`.)

**b) Testar se o script enxerga a página:**

```bash
python monitor_nt.py --teste
```

Deve listar os itens encontrados (título e link). Se vier vazio, a estrutura da página pode ter mudado ou o acesso foi bloqueado.

**c) Testar o envio com notas já existentes** (não altera a base):

```bash
python monitor_nt.py --reenviar 3
```

Envia as 3 primeiras notas da lista ao grupo/tópico, para você confirmar se o texto e os arquivos chegam corretamente.

## 8. Rodar o bot

**Contínuo** (checa a cada `INTERVALO`):

```bash
python monitor_nt.py
```

**Uma checagem só** (ideal para agendadores como cron):

```bash
python monitor_nt.py --uma-vez
```

Na **primeira execução**, o bot apenas grava a lista atual em `estado_nt.json`, sem enviar nada. A partir daí, só itens novos geram notificação.

## 9. Deixar rodando sozinho

### Linux/Mac: cron

```bash
crontab -e
```

Adicione (checagem a cada 15 minutos):

```
*/15 * * * * cd /caminho/da/pasta && TELEGRAM_TOKEN="seu_token" TELEGRAM_CHAT_ID="-1001234567890" TELEGRAM_THREAD_ID="5" /usr/bin/python3 monitor_nt.py --uma-vez >> monitor.log 2>&1
```

### Linux: serviço systemd

Crie `/etc/systemd/system/monitor-nt.service`:

```ini
[Unit]
Description=Monitor de Notas Tecnicas NF-e
After=network-online.target

[Service]
WorkingDirectory=/caminho/da/pasta
Environment=TELEGRAM_TOKEN=seu_token
Environment=TELEGRAM_CHAT_ID=-1001234567890
Environment=TELEGRAM_THREAD_ID=5
ExecStart=/usr/bin/python3 monitor_nt.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-nt
sudo systemctl status monitor-nt
```

### Windows: Agendador de Tarefas

1. Defina as variáveis de forma permanente (cmd):
   ```
   setx TELEGRAM_TOKEN "seu_token"
   setx TELEGRAM_CHAT_ID "-1001234567890"
   setx TELEGRAM_THREAD_ID "5"
   ```
   (feche e abra o terminal depois do `setx`)
2. Abra o **Agendador de Tarefas** → *Criar Tarefa Básica*.
3. Gatilho: repetir a cada 15 minutos (ou ao iniciar o Windows, se for usar o modo contínuo).
4. Ação: *Iniciar um programa*
   - Programa: caminho do `python.exe` (descubra com `where python`)
   - Argumentos: `monitor_nt.py --uma-vez`
   - Iniciar em: a pasta do script

### Qualquer sistema: segundo plano simples

```bash
nohup python3 monitor_nt.py > monitor.log 2>&1 &
```

## 10. Como o bot funciona

1. Baixa a página de Notas Técnicas e extrai os links de conteúdo (títulos + endereços).
2. Compara com os itens salvos em `estado_nt.json`.
3. Para cada item novo:
   - envia ao Telegram uma mensagem com o título e o link;
   - baixa o arquivo (diretamente, ou procurando dentro da página de detalhe) e o envia como documento;
   - grava o item no `estado_nt.json`.
4. Repete após o intervalo configurado.

Observações:

- O Telegram limita o envio de arquivos por bots a **50 MB**; acima disso, só o link é enviado.
- O bot identifica novidades pelo **link**, não pela data de publicação.
- Para reprocessar uma nota (por exemplo, para teste), apague a entrada correspondente no `estado_nt.json` e rode `python monitor_nt.py --uma-vez`. Cuide para não quebrar a sintaxe do JSON (vírgulas e chaves).
- **Nunca apague o `estado_nt.json` por engano**: na próxima execução o bot trataria tudo como primeira execução e gravaria nova base, deixando de avisar sobre notas publicadas no intervalo.

## 11. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `getUpdates` retorna `"result":[]` | Bot não recebeu mensagem, ou há webhook ativo | Mande mensagem mencionando o bot no grupo; rode `deleteWebhook` |
| `401 Unauthorized` | Token errado | Confira o token (sem espaços, sem `<` `>`) |
| `404 Not Found` na URL da API | URL montada errada | Formato: `https://api.telegram.org/bot<TOKEN>/metodo` (`bot` colado ao token) |
| `chat not found` | ID do grupo errado ou bot fora do grupo | Confira o ID (com `-`) e se o bot foi adicionado |
| `message thread not found` | ID do tópico errado ou bot sem permissão no tópico | Reconfira o ID do tópico; remova `TELEGRAM_THREAD_ID` para enviar ao Geral |
| Grupo mudou e o bot parou de enviar | Grupo virou supergrupo e o ID mudou (passa a ter prefixo `-100`) | Descubra o ID novamente |
| Mensagens vão para o tópico "Geral" | `TELEGRAM_THREAD_ID` não definido | Defina a variável |
| Erro de SSL ao acessar o site | Cadeia de certificados do site da Fazenda | Defina `VERIFICAR_SSL = False` no script |
| `--teste` lista 0 itens | Estrutura da página mudou, acesso bloqueado ou filtro de links não casa | Salve o HTML da página e ajuste a função `extrair_itens` |
| Chega só texto, sem arquivo | Link leva a uma página de detalhe com estrutura não reconhecida | Veja o log ("Não consegui anexar arquivo...") e ajuste `achar_arquivos` |
| Bot reenviou notas antigas | `estado_nt.json` foi perdido/recriado, ou o script rodou de outra pasta | Fixe o caminho do estado (seção 6) |
| `ModuleNotFoundError: requests` | Dependências não instaladas (ou ambiente virtual não ativo) | `pip install requests beautifulsoup4` |

## Segurança

- Trate o token do bot como senha. Se ele vazar, gere outro com `/revoke` no @BotFather.
- Não publique o token em repositórios (GitHub etc.). Se versionar o projeto, mantenha-o apenas em variáveis de ambiente.
