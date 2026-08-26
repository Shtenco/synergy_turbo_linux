// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// @notice Self-contained EVM accounting model for the SYNERGY two-bridge hypothesis.
/// The SYNERGY controller uses ONLY `oraclePrice6` for its own valuation/gates.
/// The foreign AMM is independent and settles from its own reserves using x*y=k.
contract OracleDrivenSynergyEVM {
    uint256 public constant BPS = 10_000;
    uint256 public constant ONE_WETH = 1e18;

    // OUR oracle: USDC-6 per 1 WETH.
    uint256 public oraclePrice6;

    // QE-resettable Fork pool target. Every cycle starts from these exact reserves.
    uint256 public immutable targetEthS;
    uint256 public immutable targetSUSD;
    uint256 public immutable internalFeeBps;

    // OUR canonical Base bridge reserves.
    uint256 public wethBridgeReserve; // 18 decimals
    uint256 public usdcBridgeReserve; // 6 decimals
    uint256 public immutable targetWethBridge;

    // FOREIGN external WETH/USDC CPMM.
    uint256 public externalWeth; // 18 decimals
    uint256 public externalUsdc; // 6 decimals
    uint256 public immutable externalFeeBps;

    // Telemetry.
    uint256 public cycles;
    uint256 public rebalances;
    uint256 public qeMintedSUSD;
    uint256 public qeAbsorbedSUSD;
    uint256 public qeAbsorbedEthS;
    uint256 public ethBridgeForkToBase;
    uint256 public ethBridgeBaseToFork;
    uint256 public usdBridgeForkToBase;
    uint256 public usdBridgeBaseToFork;

    error InsufficientWethBridge();
    error InsufficientUsdcBridge();
    error InvalidOracle();
    error InvalidFee();
    error ExternalLiquidity();

    constructor(
        uint256 oraclePrice6_,
        uint256 targetEthS_,
        uint256 targetSUSD_,
        uint256 internalFeeBps_,
        uint256 initialWethBridge_,
        uint256 initialUsdcBridge_,
        uint256 externalWeth_,
        uint256 externalUsdc_,
        uint256 externalFeeBps_
    ) {
        if (oraclePrice6_ == 0) revert InvalidOracle();
        if (internalFeeBps_ >= BPS || externalFeeBps_ >= BPS) revert InvalidFee();
        oraclePrice6 = oraclePrice6_;
        targetEthS = targetEthS_;
        targetSUSD = targetSUSD_;
        internalFeeBps = internalFeeBps_;
        wethBridgeReserve = initialWethBridge_;
        usdcBridgeReserve = initialUsdcBridge_;
        targetWethBridge = initialWethBridge_;
        externalWeth = externalWeth_;
        externalUsdc = externalUsdc_;
        externalFeeBps = externalFeeBps_;
    }

    // ---------------- OUR ORACLE / NAV ----------------

    function setOraclePrice6(uint256 newPrice6) external {
        if (newPrice6 == 0) revert InvalidOracle();
        oraclePrice6 = newPrice6;
    }

    /// @notice This is exactly the NAV seen by a system that trusts OUR oracle 100%.
    function oracleNav6() public view returns (uint256) {
        return usdcBridgeReserve + (wethBridgeReserve * oraclePrice6) / ONE_WETH;
    }

    /// @notice Foreign AMM spot price. This is NOT used by SYNERGY for its own gate.
    function externalSpotPrice6() public view returns (uint256) {
        return (externalUsdc * ONE_WETH) / externalWeth;
    }

    /// @notice Independent market-marked canonical NAV, reported only as audit telemetry.
    function marketMarkedNav6() public view returns (uint256) {
        return usdcBridgeReserve + (wethBridgeReserve * externalSpotPrice6()) / ONE_WETH;
    }

    // ---------------- QE RESETTABLE INTERNAL POOL ----------------

    /// @dev Each quote starts from target reserves because QE restores the pool after every action.
    function quoteInternalSUSDToEthS(uint256 susdIn) public view returns (uint256 ethOut) {
        uint256 netIn = (susdIn * (BPS - internalFeeBps)) / BPS;
        ethOut = (targetEthS * netIn) / (targetSUSD + netIn);
    }

    function quoteInternalEthSToSUSD(uint256 ethIn) public view returns (uint256 susdOut) {
        uint256 netIn = (ethIn * (BPS - internalFeeBps)) / BPS;
        susdOut = (targetSUSD * netIn) / (targetEthS + netIn);
    }

    // ---------------- TWO REAL-DIRECTION BRIDGE RAILS ----------------

    /// Fork ethS -> Base WETH: canonical WETH must come from OUR pre-funded reserve.
    function _forkEthSToBaseWeth(uint256 ethAmount) internal returns (uint256 wethOut) {
        if (wethBridgeReserve < ethAmount) revert InsufficientWethBridge();
        wethBridgeReserve -= ethAmount;
        ethBridgeForkToBase += ethAmount;
        return ethAmount;
    }

    /// Base WETH -> Fork ethS: canonical WETH is locked back into OUR reserve.
    function _baseWethToForkEthS(uint256 wethAmount) internal returns (uint256 ethSOut) {
        wethBridgeReserve += wethAmount;
        ethBridgeBaseToFork += wethAmount;
        return wethAmount;
    }

    /// Fork sUSD -> Base USDC: canonical USDC must come from OUR reserve.
    function _forkSusdToBaseUsdc(uint256 susdAmount) internal returns (uint256 usdcOut) {
        if (usdcBridgeReserve < susdAmount) revert InsufficientUsdcBridge();
        usdcBridgeReserve -= susdAmount;
        usdBridgeForkToBase += susdAmount;
        return susdAmount;
    }

    /// Base USDC -> Fork sUSD: canonical USDC is locked into OUR reserve.
    function _baseUsdcToForkSusd(uint256 usdcAmount) internal returns (uint256 susdOut) {
        usdcBridgeReserve += usdcAmount;
        usdBridgeBaseToFork += usdcAmount;
        return usdcAmount;
    }

    // ---------------- FOREIGN AMM ----------------

    function quoteExternalWethToUsdc(uint256 wethIn) public view returns (uint256 usdcOut) {
        uint256 netIn = (wethIn * (BPS - externalFeeBps)) / BPS;
        usdcOut = (externalUsdc * netIn) / (externalWeth + netIn);
    }

    function _externalSwapWethToUsdc(uint256 wethIn) internal returns (uint256 usdcOut) {
        usdcOut = quoteExternalWethToUsdc(wethIn);
        if (usdcOut >= externalUsdc) revert ExternalLiquidity();
        externalWeth += wethIn;
        externalUsdc -= usdcOut;
    }

    /// @notice Gross USDC needed for exact WETH output from the foreign CPMM.
    function quoteExternalUsdcForExactWeth(uint256 wethOut) public view returns (uint256 usdcIn) {
        if (wethOut >= externalWeth) revert ExternalLiquidity();
        // netIn = y * out / (x - out), rounded up.
        uint256 num = externalUsdc * wethOut;
        uint256 den = externalWeth - wethOut;
        uint256 netIn = (num + den - 1) / den;
        // gross = ceil(net * BPS / (BPS-fee)).
        uint256 feeDen = BPS - externalFeeBps;
        usdcIn = (netIn * BPS + feeDen - 1) / feeDen;
    }

    function _externalSwapUsdcForExactWeth(uint256 wethOut, uint256 usdcIn) internal {
        if (wethOut >= externalWeth) revert ExternalLiquidity();
        externalUsdc += usdcIn;
        externalWeth -= wethOut;
    }

    // ---------------- ORACLE-DRIVEN TWO-BRIDGE CYCLE ----------------

    /// @notice Forward lift used when OUR oracle marks ETH below the foreign executable market.
    /// 1) QE mints sUSD and buys ethS in our resettable Fork pool.
    /// 2) ethS -> WETH through our ETH bridge reserve.
    /// 3) WETH is sold to the FOREIGN WETH/USDC AMM.
    /// 4) received canonical USDC is locked into our USD bridge reserve -> sUSD on Fork.
    /// 5) QE absorbs the returned sUSD and resets the internal pool to target.
    function forwardOracleCycle(uint256 qeSusdIn) public returns (uint256 wethSold, uint256 usdcReceived) {
        qeMintedSUSD += qeSusdIn;
        uint256 ethSOut = quoteInternalSUSDToEthS(qeSusdIn);

        wethSold = _forkEthSToBaseWeth(ethSOut);
        usdcReceived = _externalSwapWethToUsdc(wethSold);

        uint256 forkSusdReturned = _baseUsdcToForkSusd(usdcReceived);
        qeAbsorbedSUSD += forkSusdReturned;
        cycles += 1;
    }

    /// @notice Reverse bridge rebalance. The system still uses OUR oracle for its own NAV,
    /// but canonical USDC needed to buy WETH is determined by the foreign pool reserves.
    /// This uses BOTH bridge rails in the reverse direction:
    /// sUSD->USDC, foreign USDC->WETH, WETH->ethS, then QE absorbs ethS.
    function rebalanceWethToTarget() public returns (uint256 usdcSpent, uint256 wethBought) {
        if (wethBridgeReserve >= targetWethBridge) return (0, 0);
        wethBought = targetWethBridge - wethBridgeReserve;
        usdcSpent = quoteExternalUsdcForExactWeth(wethBought);

        uint256 canonicalUsdc = _forkSusdToBaseUsdc(usdcSpent);
        _externalSwapUsdcForExactWeth(wethBought, canonicalUsdc);
        uint256 forkEthS = _baseWethToForkEthS(wethBought);
        qeAbsorbedEthS += forkEthS;
        rebalances += 1;
    }

    function runForwardCycles(uint256 n, uint256 qeSusdPerCycle) external {
        for (uint256 i = 0; i < n; ++i) {
            forwardOracleCycle(qeSusdPerCycle);
        }
    }

    function runCyclesWithBandRebalance(
        uint256 n,
        uint256 qeSusdPerCycle,
        uint256 rebalanceBelowWeth
    ) external {
        for (uint256 i = 0; i < n; ++i) {
            forwardOracleCycle(qeSusdPerCycle);
            if (wethBridgeReserve < rebalanceBelowWeth) {
                rebalanceWethToTarget();
            }
        }
    }

    /// @notice Ensures the experiment can be closed with WETH bridge restored to target.
    function finalRebalance() external {
        rebalanceWethToTarget();
    }
}
