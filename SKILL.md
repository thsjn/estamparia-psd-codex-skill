---
name: estamparia-psd
description: Criar estampas têxteis editáveis com motivos raster separados, rapport contínuo (reto, meio-salto ou tijolo), barrado de colocação, textura opcional e PSD em camadas que abre no Photoshop e em editores fora da Adobe. Use quando o pedido for estampa, padronagem, rapport, repetição contínua, all-over, estampa corrida, módulo de estampa, barrado, estampa localizada, motivos separados em camadas, PSD de estamparia, arquivo para sublimação ou estamparia digital, ou foto/mockup de roupa com a estampa. Não use para uma foto isolada sem estampa.
---

# Estamparia com PSD editável

Produz arte de tecido e arquivos de produção coerentes com as referências do usuário. A direção visual pode variar. Os invariantes técnicos não variam: motivos com transparência real, uma camada por ocorrência, repetição verificável e PSD que abre fora do psd-tools.

## 1. Entrevista (antes de gerar qualquer motivo)

Pule o que o pedido ou as referências já respondem. No Claude Code, use `AskUserQuestion`. No Codex, use uma lista numerada com opções e um padrão, para a pessoa responder "1a 2b 3 padrão".

1. **Aplicação:** a) rapport contínuo (all-over), b) arte de colocação com barrado, c) os dois. Padrão: c).
2. **Tipo de repetição:** a) reta, b) meio-salto (half-drop, esconde melhor a grade), c) tijolo (brick). Padrão: b) para floral e orgânico, a) para geométrico.
3. **Tamanho do módulo e resolução:** em cm e dpi, ou em px. Padrão: 2400 × 2400 px a 300 dpi (20,3 cm). Em meio-salto a altura precisa ser par; em tijolo, a largura.
4. **Paleta e fundo:** cores com hex, ou "igual à referência".
5. **Motivos obrigatórios e hierarquia:** herói, secundários e preenchimento; densidade (aberta, média, fechada).
6. **Textura:** linho fino, trama de algodão, aquarela sobre papel, cetim discreto ou nenhuma. Padrão: nenhuma no rapport e opcional só na colocação.
7. **Destino:** sublimação, estamparia digital, silk ou só apresentação. Se for gráfica com CMYK ou perfil ICC, avise que a saída é RGB 8 bits e precisa de conversão na produção.

Se faltar referência visual para um estilo específico, peça imagens ou links junto com as perguntas, numa mensagem só.

## 2. Direção da estampa

Escreva antes de gerar: lista de motivos, hierarquia, escala relativa, densidade, ritmo, cor, área de respiro e posição do barrado. Para foto de roupa, descreva modelagem, mapa de aplicação da estampa, cenário, luz e enquadramento. Se a skill `diretor-de-imagem` estiver instalada, use-a para a direção de foto e mockup.

## 3. Motivos

- Gere cada motivo distinto como PNG isolado com **canal alfa verdadeiro**, margem transparente, sem tecido, sombra, texto ou fundo retangular. Use a skill `imagegen` do ambiente e os modelos de prompt de [references/prompts-motivos.md](references/prompts-motivos.md).
- Confira o alfa antes de compor. Um xadrez desenhado na imagem não é transparência. O compositor recusa PNG sem alfa ou sem área transparente.
- Crie arquivos separados para tudo o que o usuário deve mover no Photoshop. Repetições de um mesmo motivo podem usar a mesma origem, mas cada ocorrência vira uma camada própria. Partes pintadas dentro de um motivo continuam unidas, salvo pedido de separação mais fina.

## 4. Composição e PSD

Monte um manifesto ([references/manifest.md](references/manifest.md)) e rode:

```bash
python scripts/compose_psd.py --manifest caminho/manifest.json --verify
```

- O compositor envolve nas bordas opostas o motivo que cruza o módulo, conforme o tipo de repetição.
- **Motivo que cruza a borda vira camadas separadas, uma por peça** ("Flor 01 (peça 1 de 3)"). Mover uma peça sozinha quebra o rapport. Para reposicionar, mude `center` no manifesto e rode de novo.
- **O barrado é arte de colocação,** nunca repetição vertical. Ele sai num PNG transparente separado e só entra no PSD de colocação. O compositor avisa quando o barrado cobre algum motivo.
- **A textura é repetida, não esticada,** e fica numa camada própria com opacidade e modo de mesclagem (`multiply` por padrão) editáveis no Photoshop. Ela só entra no rapport com `include_in_repeat: true`. Nesse caso, o tamanho dela precisa dividir o módulo, e o compositor avisa se não dividir.
- O PSD é RGB 8 bits com compressão RLE, a mesma que o Photoshop usa, e não leva grupos de camada. Nomes com acento aparecem no Photoshop; o campo de nome antigo recebe a versão sem acento.

## 5. Validação (obrigatória antes de entregar)

Leia o `<name>_checks.json`:

- `verify_tile_psd.ok` e `verify_placement_psd.ok` precisam ser `true`. Eles conferem a contagem de camadas, a camada do topo e a renderização das camadas contra o PNG (tolerância de 3 em 255), e usam um segundo leitor (Pillow) para decodificar a imagem achatada.
- `vertical_diagnostic_pass` e `horizontal_diagnostic_pass` mostram se a emenda segue o tipo de repetição. São diagnóstico: abra também a prévia 2 × 2.
- `warnings`: trate cada aviso ou explique ao usuário por que ele foi aceito.
- Se houver Photoshop ou outro editor disponível, abra o PSD. Se não houver, diga que a abertura interativa ficou pendente.

## 6. Entrega

PSD do módulo, PSD de colocação, PNG do módulo, PNG de colocação, prévia 2 × 2, barrado separado quando houver, motivos originais, manifesto e direção da estampa. Diferencie a foto ou mockup gerado do arquivo técnico de impressão.

## Exemplo e teste de instalação

```bash
python scripts/criar_exemplo.py examples/jardim
python scripts/compose_psd.py --manifest examples/jardim/manifest.json --verify
```
