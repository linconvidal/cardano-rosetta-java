package org.cardanofoundation.rosetta.api.block.model.entity;

import java.math.BigInteger;
import java.util.List;
import java.util.Set;
import jakarta.persistence.*;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import com.bloxbean.cardano.yaci.core.model.Relay;
import io.hypersistence.utils.hibernate.type.json.JsonType;
import org.hibernate.annotations.Type;

@Getter
@Setter
@NoArgsConstructor
@Entity
@Table(name = "pool_registration")
@IdClass(PoolRegistrationId.class)
public class PoolRegistrationEntity {

  @Id
  @Column(name = "tx_hash")
  private String txHash;

  @Id
  @Column(name = "cert_index")
  private int certIndex;

  @Column(name = "pool_id")
  private String poolId;

  @Column(name = "vrf_key")
  private String vrfKeyHash;

  @Column(name = "pledge")
  private BigInteger pledge;

  @Column(name = "cost")
  private BigInteger cost;

  @Column(name = "margin")
  private Double margin;

  @Column(name = "reward_account")
  private String rewardAccount;

  @Type(JsonType.class)
  @Column(columnDefinition = "TEXT") // Use TEXT for H2
  private Set<String> poolOwners;

  @Type(JsonType.class)
  @Column(columnDefinition = "TEXT") // Use TEXT for H2
  private List<Relay> relays;

}
