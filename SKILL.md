---
name: estamparia-psd
description: Criar estampas têxteis em rapport ou colocação com motivos raster separados, texturas opcionais, barrado e PSD em camadas. Use para projetos de estamparia editável, não para uma foto isolada sem estampa.
---

# Estamparia com PSD editável

Produza arte de tecido e arquivos de produção coerentes com as referências do usuário. A direção visual pode variar; os invariantes técnicos são transparência real dos motivos, camadas separadas e repetição verificável quando houver rapport.

## Entrada e direção

- Inspecione referências já fornecidas e os arquivos do projeto. Identifique se cada imagem é referência de linguagem visual, modelagem, composição ou arte a reaproveitar. Não trate uma foto de roupa como módulo de impressão sem confirmação.
- Se faltar referência visual para uma solicitação de estilo específico, peça ao usuário imagens ou links e agrupe as demais decisões essenciais na mesma pergunta: aplicação (rapport contínuo, arte de colocação ou ambos), dimensões/resolução, paleta, motivos obrigatórios e destino dos arquivos. Continue o trabalho independente enquanto aguarda. Se a solicitação já trouxer referência suficiente, avance.
- Escreva uma direção de cena/estampa antes da geração: lista de motivos, hierarquia, densidade, escala, ritmo, cor, área de respiro e posição do barrado. Para fotos de roupa, descreva modelagem, mapa de aplicação da estampa, cenário, luz e enquadramento.
- Ofereça textura como escolha de acabamento quando relevante: linho fino, trama de algodão, aquarela sobre papel, cetim discreto ou nenhuma. Não aplique textura por padrão se ela prejudicar leitura, transparência ou repetição. Separe a textura em camada própria.

## Motivos e composição

- Para criar ou editar imagens raster, siga a skill `imagegen` disponível no ambiente. Gere cada motivo distinto como PNG isolado com canal alfa verdadeiro, margem transparente e sem tecido, sombra, texto ou fundo retangular. Inspecione o alfa e recorte margens vazias antes de compor.
- Crie arquivos separados para elementos que o usuário deve mover no Photoshop. Não agrupe aves, flores ou folhas distintas em uma única origem se o pedido exige movê-las individualmente. Repetições de um mesmo motivo podem usar a mesma origem, mas cada ocorrência no PSD deve ser uma camada própria com nome claro. Informe que partes pintadas dentro de um motivo permanecem unidas, salvo pedido de separação mais fina.
- Monte o rapport por composição determinística dos PNGs sobre um módulo. Quando um motivo cruza a borda, envolva a mesma ocorrência na borda oposta. Gere uma prévia 2 × 2 e inspecione as quatro emendas, além de calcular diferenças de borda.
- Trate o barrado de bainha como arte de colocação independente. O módulo all-over pode repetir em ambas as direções; a arte de colocação com barrado na base não deve ser apresentada como repetição vertical contínua. Exporte o barrado transparente separadamente.
- Se a textura fizer parte do rapport, use textura que também repita sem emendas. Se for só acabamento de apresentação, aplique-a apenas à arte de colocação.
- Se o usuário pedir foto de roupa ou mockup, use os arquivos da estampa como referência de aplicação e diferencie a visualização gerada do encaixe técnico de impressão. Preserve a modelagem indicada e registre o mapa dos motivos e barrados na roupa.

## Entrega e validação

- Para composição raster e PSD em camadas, use `scripts/compose_psd.py` com o esquema de `references/manifest.md` quando atender ao caso; adapte o script ou o projeto quando houver exigências especiais de perfil de cor, canais, separação ou encaixe.
- O script usa Pillow, NumPy e pytoshop; psd-tools verifica o PSD. As dependências estão em `requirements.txt`. Confirme a instalação no ambiente do projeto; não suponha que a skill instala bibliotecas ao ser invocada.
- Verifique tamanho, resolução, modo de cor, transparência dos motivos, nomes/contagem de camadas, composição do PSD contra o PNG, continuidade visual do rapport e posição do barrado. Abra no Photoshop quando disponível; se não estiver disponível, declare essa verificação pendente.
- Entregue PSD, PNG de colocação, PNG do módulo, prévia 2 × 2, barrado separado quando aplicável, motivos originais e direção de cena. Diferencie visualização gerada de foto/mockup e arquivo técnico de impressão.
