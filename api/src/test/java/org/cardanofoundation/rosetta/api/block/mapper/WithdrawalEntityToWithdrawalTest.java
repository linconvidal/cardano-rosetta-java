package org.cardanofoundation.rosetta.api.block.mapper;

import java.math.BigInteger;

import org.springframework.beans.factory.annotation.Autowired;

import org.junit.jupiter.api.Test;

import org.cardanofoundation.rosetta.api.BaseMapperSetup;
import org.cardanofoundation.rosetta.api.block.model.domain.Withdrawal;
import org.cardanofoundation.rosetta.api.block.model.entity.WithdrawalEntity;

import static org.assertj.core.api.AssertionsForClassTypes.assertThat;

public class WithdrawalEntityToWithdrawalTest extends BaseMapperSetup {

  @Autowired
  private WithdrawalEntityToWithdrawal my;

  @Test
  public void fromEntity() {
    WithdrawalEntity from = newWithdrawalEntity();
    Withdrawal into = my.fromEntity(from);

    assertThat(into.getStakeAddress()).isEqualTo(from.getAddress());
    assertThat(into.getAmount()).isEqualTo(from.getAmount());
  }

  private WithdrawalEntity newWithdrawalEntity() {
    return new WithdrawalEntity("address", null, BigInteger.ONE);
  }

}
