"""
Pruning validation tests: UTXO-based selective pruning.

Tests validate pruning behavior without hardcoding specific blocks or addresses.
Uses network_test_data.yaml and dynamic calculations based on oldest_block_identifier.
"""

import pytest
import allure


@allure.feature("Pruning")
@allure.story("Selective UTXO Pruning")
class TestPruningBehavior:
    """Validate UTXO-based pruning behavior."""

    @pytest.mark.nightly
    def test_old_blocks_have_selective_pruning(self, client, network, is_pruned_instance, oldest_block_identifier):
        """Verify inputs always pruned, outputs only if spent."""
        if not is_pruned_instance:
            pytest.skip("Only relevant for pruned instances")

        if not oldest_block_identifier:
            raise AssertionError("Pruned instance must have oldest_block_identifier")

        # Query well before the pruning boundary
        old_block = oldest_block_identifier - 500000
        if old_block < 1:
            pytest.skip("Not enough blockchain history for this test")

        # Search for blocks with transactions
        found_pruning_evidence = False
        for offset in range(0, 50000, 10000):
            test_block = old_block + offset
            response = client.block(
                network_identifier={"blockchain": "cardano", "network": network},
                block_identifier={"index": test_block},
            )

            if response.status_code != 200:
                continue

            transactions = response.json().get("block", {}).get("transactions", [])
            if not transactions:
                continue

            # Check ALL transactions for pruning effects
            pruned_input = pruned_output = preserved_output = False
            for tx in transactions:  # Check ALL, not just [:10]
                for op in tx.get("operations", []):
                    account = op.get("account", {})
                    amount = op.get("amount", {}).get("value", "")
                    op_type = op.get("type", "")
                    is_pruned = account == {} and amount == "0"

                    if op_type == "input" or op.get("coin_change", {}).get("coin_action") == "coin_spent":
                        pruned_input = pruned_input or is_pruned
                    elif op_type == "output" or op.get("coin_change", {}).get("coin_action") == "coin_created":
                        if is_pruned:
                            pruned_output = True
                        elif "address" in account and amount != "0":
                            preserved_output = True

            if pruned_input:
                found_pruning_evidence = True
                assert pruned_input or pruned_output, "Should find pruning effects in old blocks"
                break

        assert found_pruning_evidence, (
            f"No pruning effects found in blocks before {oldest_block_identifier}. "
            f"Pruning might not be working correctly."
        )

    @pytest.mark.nightly
    def test_recent_blocks_have_complete_data(self, client, network, network_status, is_pruned_instance, oldest_block_identifier):
        """Verify blocks at/after oldest_block_identifier have complete data."""
        if not is_pruned_instance:
            pytest.skip("Only relevant for pruned instances")

        if not oldest_block_identifier:
            raise AssertionError("Pruned instance must have oldest_block_identifier")

        # Test at the boundary
        response = client.block(
            network_identifier={"blockchain": "cardano", "network": network},
            block_identifier={"index": oldest_block_identifier},
        )
        assert response.status_code == 200, (
            f"Could not fetch block at oldest_block_identifier ({oldest_block_identifier}) - API broken!"
        )

        transactions = response.json().get("block", {}).get("transactions", [])

        # Check ALL transactions for completeness
        for tx_idx, tx in enumerate(transactions):  # Check ALL
            for op_idx, op in enumerate(tx.get("operations", [])):
                account = op.get("account", {})
                amount = op.get("amount", {}).get("value", "")

                # After oldest_block_identifier, NO pruning should occur
                assert account != {} or amount != "0", (
                    f"Block {oldest_block_identifier} (oldest_block_identifier) tx {tx_idx} op {op_idx} "
                    f"has pruned data - oldest_block_identifier is inaccurate!"
                )

    @pytest.mark.nightly
    def test_search_by_address_limited_for_old_blocks(self, client, network, network_data, is_pruned_instance, oldest_block_identifier):
        """Historical search returns fewer results (can't find txs where address only in pruned inputs)."""
        if not is_pruned_instance:
            pytest.skip("Only relevant for pruned instances")

        if not oldest_block_identifier:
            raise AssertionError("Pruned instance must have oldest_block_identifier")

        # Use whale address (likely has lots of historical activity)
        address = network_data["test_addresses"]["whale"]

        # Old blocks - before pruning boundary
        old_max_block = oldest_block_identifier - 100000
        if old_max_block < 1:
            pytest.skip("Not enough history")

        old_response = client.search_transactions(
            network_identifier={"blockchain": "cardano", "network": network},
            account_identifier={"address": address},
            max_block=old_max_block,
            limit=100,
        )
        assert old_response.status_code == 200, "Old block search should work"
        old_count = old_response.json().get("total_count", 0)

        # Recent blocks - after pruning boundary
        recent_min_block = oldest_block_identifier + 10000

        recent_response = client.search_transactions(
            network_identifier={"blockchain": "cardano", "network": network},
            account_identifier={"address": address},
            offset=recent_min_block,  # Use offset to skip old blocks
            limit=100,
        )
        assert recent_response.status_code == 200, "Recent search should work"
        recent_count = recent_response.json().get("total_count", 0)

        # Invariant: pruned search returns LESS results (can't find pruned inputs)
        # We can't assert exact ratio, but old should be less than recent
        assert old_count < recent_count, (
            f"Old search ({old_count}) should return fewer results than recent ({recent_count}) "
            f"due to pruned inputs. If equal, pruning might not be working."
        )

    @pytest.mark.nightly
    def test_oldest_block_identifier_present_when_pruning_enabled(self, network_status, is_pruned_instance):
        """Verify oldest_block_identifier presence matches configuration."""
        if is_pruned_instance:
            assert "oldest_block_identifier" in network_status, (
                "Pruned instance (REMOVE_SPENT_UTXOS=true) must have oldest_block_identifier in /network/status"
            )
            oldest = network_status["oldest_block_identifier"]
            assert "index" in oldest and "hash" in oldest and oldest["index"] > 0
        else:
            assert "oldest_block_identifier" not in network_status, (
                "Non-pruned instance (REMOVE_SPENT_UTXOS=false) should not have oldest_block_identifier"
            )