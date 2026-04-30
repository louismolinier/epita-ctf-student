# AUDIT — EPITA Évaluation 2026 : Blockchain & Sécurité

**Auteur** : Louis Molinier
**Réseau** : Sepolia Testnet
**Cible `FairCasino`** : `0xed5415679D46415f6f9a82677F8F4E9ed9D1302b`

---

## 1. Résumé Exécutif

Pour exploiter la cible (la loterie `FairCasino`), la consigne imposait d'opérer un drain complet et atomique des fonds gagnés vers 3 lieutenants selon une répartition exacte (50% / 30% / 20%). 
L'analyse de la cible sur Sepolia a mis en évidence une vulnérabilité critique de prédictibilité due à la transparence inhérente de la blockchain. Le contrat base sa logique pseudo-aléatoire sur des variables prétendument privées mais entièrement lisibles on-chain.

## 2. Découverte de la vulnérabilité

### 2.1 Les variables "Secrètes"
Dans le smart contract de `FairCasino`, le `winningNumber` est dicté par la formule suivante (analysable par décompilation ou lecture du storage) :
$$ winningNumber = uint256(keccak256(abi.encodePacked(secretTarget \oplus price, gameSalt, currentRound))) $$

Bien que le `secretTarget` et le `gameSalt` aient été définis en `private` au sein du code cible, Ethereum assure une transparence absolue de l'état (storage state). Les données peuvent être lues, ou plus facilement encore, retrouvées directement depuis les arguments du constructeur de `FairCasino` sur Sepolia Etherscan :
- **secretTarget** : `463646446423265643233525262662355635362666463`
- **gameSalt** : `7192271`

De plus, les autres variables dynamiques `price` (via l'Oracle public Chainlink `0x1b44...`) et `currentRound` (via `casino.currentRound()`) sont récupérables à tout instant par simple appel API (RPC read-only).

### 2.2 Proof of Work de `msg.sender`
La seconde sécurité est un simple Proof-of-Work (PoW). Le Casino impose un `nonce` validant que le hachage final `keccak256(abi.encodePacked(msg.sender, round, guess, nonce))` se termine par le motif de seize bits : `0xBEEF`.
S'agissant d'un bruteforce rudimentaire modéré (cible à 65536 essais moyens), le nonce peut aisément être pré-miné off-chain grâce à un script.

## 3. Stratégie d'Attaque Atomique et Intégrité

### 3.1 Protection face à l'environnement concurrentiel (Front-running)
Sachant que d'autres cellules de l'APT28 (et d'autres étudiants) interagissent potentiellement avec la même cible au même moment, j'ai garanti une atomicité stricte des opérations. Si la logique s'exécutait en plusieurs transactions (ex. `play()` puis `distribute()`), un attaquant ou un bot MEV pourrait siphonner les fonds reçus par mon Drainer avant ma seconde transaction. 

### 3.2 Le contrat `Drainer.sol`
Comme exigé par le groupe APT28, un smart contract (`Drainer.sol`) a été rédigé. 
- Il implémente scrupuleusement l'interface `IDrainer`.
- Sa méthode `attack()` inclut l'appel payant de `0.01 ether` au casino avec nos paramètres précalculés.
- Dès que le `FairCasino` renvoie les fonds au Drainer si le pari est gagnant, l'attaque appelle immédiatement `distribute()` dans la même stack d'exécution (la même transaction). Cette fonction sécurisée assure le virement des pourcentages exigés (50% pour LT1, 30% pour LT2, 20% pour LT3) avant même qu'une autre entité ne puisse interagir. Si quoi que ce soit échoue (absence de liquidité ou erreur interne), la transaction *revert* afin qu'aucun fond ne soit bloqué à mi-chemin.

### 3.3 L'exécutable Off-Chain (`solve.py`)
Un script Python, fonctionnant avec `web3py`, effectue toutes les lectures au préalable :
1. Fetch en temps réel du `price` de l'oracle de testnet Chainlink.
2. Fetch du `currentRound`.
3. Calcul du `winningNumber` en suivant la même logique d'encodage Solidity (XOR + EncodePacked + Keccak256).
4. Bruteforce ultra-rapide (en local CPU) du `nonce` valide avec pour base l'adresse (sender) de notre Drainer fraîchement déployé.
5. Signature et Broadcast de la transaction contenant le payload d'attaque, via la clé privée, interagissant avec la fonction `attack` du contrat Drainer.

## 4. Traçabilité de l'Exploitation (Preuves On-Chain)
Afin de prouver la réussite absolue de l'attaque en répondant à la demande des 3 "strikes" imposée par l'APT28, voici les traces de l'opération sur le réseau Sepolia :

- **Attaquant (EOA)** : `0x04e41774B43bD734FeD4a531791c92Dc1ba2C146`
- **Smart Contract (Drainer)** : `0x8dd21C76160a843596Be1b73eabF1977f0A450c8`
    - [Hash de déploiement](https://sepolia.etherscan.io/tx/0xd47318bf1e5b2ce8c83b7ba02f26e5b74cfc8794b8cb54e8f19cefbdf8449d9c)

- **Frappes Atomiques (x3)** :
    1. Strike 1 : [0xdd01afa2df17914fe18452b4cdec7b5ad8dea46a1fa25e87740cf76bb85a5feb](https://sepolia.etherscan.io/tx/0xdd01afa2df17914fe18452b4cdec7b5ad8dea46a1fa25e87740cf76bb85a5feb)
    2. Strike 2 : [0x14466ae2b620e5e6543713b9fc76bf564480516b3219e1d0b3641f53e26cabb3](https://sepolia.etherscan.io/tx/0x14466ae2b620e5e6543713b9fc76bf564480516b3219e1d0b3641f53e26cabb3)
    3. Strike 3 : [0xe44be29b9f32a746ab82343142e2b8b17f945731223b7dbf2c351582392851eb](https://sepolia.etherscan.io/tx/0xe44be29b9f32a746ab82343142e2b8b17f945731223b7dbf2c351582392851eb)

Sur chaque transaction d'attaque, on peut observer les flux irréfutables confirmant le succès de la logique d'atomicité : 
- Envoi initial au casino (`0.01 ETH`).
- Gain de la cible ("jackpot").
- Distribution immédiate et finale selon les taux de répartition prévus (50/30/20) vers les lieutenants dans la même exécution de contrat.

## 5. Conclusion
L'exploitation démontre qu'aucun aléa ne doit être généré à partir de variables on-chain "hashées" dans un environnement VM transparent. Des solutions telles que Chainlink VRF sont incontournables et requises pour ce niveau de sécurité.
En l'état, l'APT28 peut impunément soutirer le jackpot au fur et à mesure que la réserve opérationnelle se remplit. Conformément à la requête, les fonds atterrissent dans les vaults des lieutenants, prouvant de manière fiable et irréfutable un contrôle total sur cette attaque logicielle.