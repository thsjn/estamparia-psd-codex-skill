# Estamparia PSD (skill para Codex e Claude Code)

Skill para criar estampas têxteis com motivos raster separados, rapport contínuo (reto, meio-salto ou tijolo), barrado de colocação, textura opcional e PSD em camadas.

Ela entrevista a pessoa (aplicação, repetição, tamanho, paleta, motivos, textura, destino), escreve a direção da estampa, orienta a geração de cada motivo com fundo transparente e monta tudo num compositor determinístico. O compositor entrega um PSD que o Photoshop e outros editores abrem, com uma camada por ocorrência de motivo.

## Instalação

A pasta precisa se chamar `estamparia-psd`.

Codex:

```bash
git clone https://github.com/thsjn/estamparia-psd-codex-skill ~/.codex/skills/estamparia-psd
```

Claude Code:

```bash
git clone https://github.com/thsjn/estamparia-psd-codex-skill ~/.claude/skills/estamparia-psd
```

Dependências do compositor (Python 3.10 ou mais novo):

```bash
python -m pip install -r requirements.txt
```

Teste de instalação, que gera um projeto de exemplo e o compõe:

```bash
python scripts/criar_exemplo.py examples/jardim
python scripts/compose_psd.py --manifest examples/jardim/manifest.json --verify
```

O comando termina sem erro e grava `examples/jardim/output/` com os PSDs, os PNGs, a prévia 2 × 2 e o `jardim_checks.json`.

No Codex, invoque com `$estamparia-psd`. No Claude Code, a skill é acionada por pedidos de estampa, rapport ou barrado.

## O que o compositor garante

- **Ordem de camadas correta:** fundo embaixo e textura no topo.
- **Compressão RLE,** a mesma que o Photoshop usa em 8 bits. A versão anterior gravava em ZIP, que vários editores fora da Adobe não decodificam.
- **Sem grupos de camada.** Motivo que cruza a borda vira camadas vizinhas, uma por peça.
- **Verificação real:** renderiza as camadas, sem confiar na imagem achatada guardada no arquivo, e decodifica o resultado com um segundo leitor.
- **Avisos:** barrado cobrindo motivo, textura que não emenda e motivo maior que o módulo.

## Limites

A saída é RGB 8 bits. Trabalhos que exigem CMYK, perfil ICC ou especificação de gráfica precisam de conversão e conferência na produção. A abertura no Photoshop não é testada automaticamente.

Veja [SKILL.md](SKILL.md) para o fluxo completo, [references/manifest.md](references/manifest.md) para o manifesto e [references/prompts-motivos.md](references/prompts-motivos.md) para gerar os motivos.

## Licença

MIT
