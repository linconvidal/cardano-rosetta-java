package org.cardanofoundation.rosetta.common.ledgersync;

import org.cardanofoundation.rosetta.common.ledgersync.kafka.AbstractBlock;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Getter
@AllArgsConstructor
@NoArgsConstructor
@ToString
@EqualsAndHashCode(callSuper = true)
@Builder
public class Block extends AbstractBlock {

  public static final String TYPE = "Block";


  private BlockHeader header;

  @Builder.Default
  private List<TransactionBody> transactionBodies = new ArrayList<>();

  private List<Witnesses> transactionWitness = new ArrayList<>();
  private Map<Integer, AuxData> auxiliaryDataMap = new LinkedHashMap<>();
  private List<Integer> invalidTransactions = new ArrayList<>();
  private List<Object> transactionMetadataSet;

  @Override
  public String getType() {
    return TYPE;
  }

  @Override
  public String getBlockHash() {
    return getHeader().getHeaderBody().getBlockHash();
  }

  @Override
  public long getSlot() {
    return getHeader().getHeaderBody().getSlotId().getSlotId();
  }

  @Override
  public long getBlockNumber() {
    return getHeader().getHeaderBody().getBlockNumber();
  }

  @Override
  public String getPreviousHash() {
    return getHeader().getHeaderBody().getPrevHash();
  }

}
