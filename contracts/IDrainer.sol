// SPDX-License-Identifier: MIT
pragma solidity 0.8.34;

interface IDrainer {
    /**
     * @notice Main entry point required by APT28 monitoring bots.
     * @param _guess Predicted winning number calculated via storage/oracle analysis.
     * @param _round Current active round ID of the target contract.
     * @param _nonce Cryptographic signature mined to satisfy the protocol's required computational difficulty threshold.
     */
    function attack(uint256 _guess, uint256 _round, uint256 _nonce) external payable;

    /**
     * @notice Mandatory Splitter module.
     * Must redistribute the entire balance of the attack contract to the 3 lieutenants.
     */
    function distribute() external;
}