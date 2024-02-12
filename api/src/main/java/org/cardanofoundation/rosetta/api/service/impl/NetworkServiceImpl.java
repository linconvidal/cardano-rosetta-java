package org.cardanofoundation.rosetta.api.service.impl;


import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.parser.OpenAPIV3Parser;
import jakarta.annotation.PostConstruct;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.io.IOUtils;
import org.cardanofoundation.rosetta.api.common.constants.Constants;
import org.cardanofoundation.rosetta.api.common.enumeration.OperationType;
import org.cardanofoundation.rosetta.api.common.enumeration.OperationTypeStatus;
import org.cardanofoundation.rosetta.api.config.RosettaConfig;
import org.cardanofoundation.rosetta.api.exception.ExceptionFactory;
import org.cardanofoundation.rosetta.api.exception.ServerException;
import org.cardanofoundation.rosetta.api.mapper.DataMapper;
import org.cardanofoundation.rosetta.api.model.Network;
import org.cardanofoundation.rosetta.api.model.NetworkStatus;
import org.cardanofoundation.rosetta.api.model.Peer;
import org.cardanofoundation.rosetta.api.model.Producer;
import org.cardanofoundation.rosetta.api.model.PublicRoot;
import org.cardanofoundation.rosetta.api.model.TopologyConfig;
import org.cardanofoundation.rosetta.api.model.rest.MetadataRequest;
import org.cardanofoundation.rosetta.api.model.rest.NetworkListResponse;
import org.cardanofoundation.rosetta.api.model.rest.NetworkOptionsResponse;
import org.cardanofoundation.rosetta.api.model.rest.NetworkRequest;
import org.cardanofoundation.rosetta.api.model.rest.NetworkStatusResponse;
import org.cardanofoundation.rosetta.api.projection.dto.BlockDto;
import org.cardanofoundation.rosetta.api.projection.dto.GenesisBlockDto;
import org.cardanofoundation.rosetta.api.service.LedgerDataProviderService;
import org.cardanofoundation.rosetta.api.service.NetworkService;
import org.cardanofoundation.rosetta.api.util.RosettaConstants;
import org.cardanofoundation.rosetta.api.util.cli.CardanoNode;
import org.json.JSONObject;
import org.openapitools.client.model.Allow;
import org.openapitools.client.model.BalanceExemption;
import org.openapitools.client.model.Error;
import org.openapitools.client.model.OperationStatus;
import org.openapitools.client.model.Version;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@RequiredArgsConstructor
public class NetworkServiceImpl implements NetworkService {

  private final RosettaConfig rosettaConfig;


  private final LedgerDataProviderService ledgerDataProviderService;


  private List<BalanceExemption> balanceExemptions;


  @Value("${cardano.rosetta.GENESIS_SHELLEY_PATH}")
  private String genesisPath;

  @Value("${cardano.rosetta.CARDANO_NODE_PATH}")
  private String cardanoNodePath;
  private final ResourceLoader resourceLoader;

  private String networkId;
  private Integer networkMagic;

  @PostConstruct
  public void filePathExistingValidator() throws ServerException {
//    validator(topologyFilepath);
    validator(genesisPath);
//    validator(cardanoNodePath); // TODO Removed to get it working clean
  }

  private void validator( String path) throws ServerException {
    if(!new File(path).exists()) {
      throw ExceptionFactory.configNotFoundException();
    }
  }

//  private List<BalanceExemption> loadExemptionsFile() {
//    if (exemptionPath != null) {
//      final ObjectMapper objectMapper = new ObjectMapper();
//      try {
//        String content = fileReader(exemptionPath);
//        balanceExemptions = objectMapper.readValue(
//            content,
//            new TypeReference<>() {
//            });
//      } catch (IOException e) {
//        e.printStackTrace();
//        return new ArrayList<>();
//      }
//    } else {
//      balanceExemptions = List.of();
//    }
//    return balanceExemptions;
//  }

  private String fileReader(String path) throws IOException {
    //check if path exists in classpath
    try (
        InputStream input = new FileInputStream(path)
    ) {
      byte[] fileBytes = IOUtils.toByteArray(input);
      return new String(fileBytes, StandardCharsets.UTF_8);
    }
  }

  @Override
  public NetworkListResponse getNetworkList(MetadataRequest metadataRequest)
      throws IOException {
    log.info("[networkList] Looking for all supported networks");
    Network supportedNetwork = getSupportedNetwork();
    return DataMapper.mapToNetworkListResponse(supportedNetwork);
  }

  @Override
  public NetworkOptionsResponse getNetworkOptions(NetworkRequest networkRequest)
      throws IOException, InterruptedException {
    log.info("[networkOptions] Looking for networkOptions");
    InputStream openAPIStream = resourceLoader.getResource(
        "classpath:/rosetta-specifications-1.4.15/api.yaml").getInputStream();
    OpenAPI openAPI = new OpenAPIV3Parser().readContents(new String(openAPIStream.readAllBytes()),
            null,
            null)
        .getOpenAPI();
    String rosettaVersion = openAPI.getInfo().getVersion();
    String implementationVersion = rosettaConfig.getImplementationVersion();

    String cardanoNodeVersion = CardanoNode.getCardanoNodeVersion(cardanoNodePath);
    OperationStatus success = new OperationStatus().successful(true)
        .status(OperationTypeStatus.SUCCESS.getValue());
    OperationStatus invalid = new OperationStatus().successful(false)
        .status(OperationTypeStatus.INVALID.getValue());
    List<OperationStatus> operationStatuses = List.of(success, invalid);

    return NetworkOptionsResponse.builder()
        .version(new Version().nodeVersion(cardanoNodeVersion)
            .rosettaVersion(rosettaVersion)
            .middlewareVersion(implementationVersion)
            .metadata(new LinkedHashMap<>()))
        .allow(new Allow().operationStatuses(operationStatuses)
            .operationTypes(
                Arrays.stream(OperationType.values()).map(OperationType::getValue).toList())
            .errors(RosettaConstants.ROSETTA_ERRORS.stream()
                .map(error ->
                    new Error().code(error.getCode())
                        .message(error.getMessage())
                        .retriable(error.isRetriable())
                        .description(error.getDescription())
                        .code(error.getCode())
                )
                .sorted(Comparator.comparingInt(Error::getCode))
                .toList())
            .historicalBalanceLookup(true)
            .callMethods(new ArrayList<>())
//            .balanceExemptions(loadExemptionsFile()) // TODO Removed to get it working clean - add balance exemptions
            .mempoolCoins(false))
        .build();
  }

  @Override
  public NetworkStatusResponse getNetworkStatus(NetworkRequest networkRequest)
      throws  IOException {
    log.debug("[networkStatus] Request received:" + networkRequest.toString());
    log.info("[networkStatus] Looking for latest block");
    NetworkStatus networkStatus = networkStatus();
    return DataMapper.mapToNetworkStatusResponse(networkStatus);
  }

  @Override
  public Network getSupportedNetwork() throws IOException {

    String content = fileReader(genesisPath);
    JSONObject object = new JSONObject(content);
    networkId = ((String) object.get("networkId")).toLowerCase();
    networkMagic = (Integer) object.get("networkMagic");

    if (networkId.equals("mainnet")) {
      return Network.builder().networkId(networkId).build();
    } else if (Objects.equals(networkMagic, Constants.PREPROD_NETWORK_MAGIC)) {
      return Network.builder().networkId("preprod").build();
    } else if (Objects.equals(networkMagic, Constants.TESTNET_NETWORK_MAGIC)) {
      return Network.builder().networkId("testnet").build();
    } else if(Objects.equals(networkMagic, Constants.DEVNET_NETWORK_MAGIC)) {
      return Network.builder().networkId("devnet").build();
    } else {
//      throw ExceptionFactory.invalidNetworkIdException();
    }
    return null;
  }

  private NetworkStatus networkStatus() throws  IOException {
    log.info("[networkStatus] Looking for latest block");
    BlockDto latestBlock = ledgerDataProviderService.findLatestBlock();
    log.debug("[networkStatus] Latest block found " + latestBlock);
    log.debug("[networkStatus] Looking for genesis block");
    GenesisBlockDto genesisBlock = ledgerDataProviderService.findGenesisBlock();
    log.debug("[networkStatus] Genesis block found " + genesisBlock);

    ObjectMapper mapper = new ObjectMapper();
//    String content = fileReader(topologyFilepath);
    String content = "";
    TopologyConfig topologyConfig = mapper.readValue(content, TopologyConfig.class);

    return NetworkStatus.builder()
        .latestBlock(latestBlock)
        .genesisBlock(genesisBlock)
        .peers(getPeerFromConfig(topologyConfig))
        .build();
  }

  private List<Peer> getPeerFromConfig(TopologyConfig topologyFile) {
    log.info("[getPeersFromConfig] Looking for peers from topologyFile");
    List<Producer> producers = Optional.ofNullable(topologyFile).map(
            TopologyConfig::getProducers)
        .orElseGet(() -> getPublicRoots(topologyFile.getPublicRoots()));
    log.debug("[getPeersFromConfig] Found " + producers.size() + " peers");
    return producers.stream().map(producer -> new Peer(producer.getAddr())).toList();
  }

  private List<Producer> getPublicRoots(List<PublicRoot> publicRoots) {
    if (publicRoots == null) {
      return new ArrayList<>();
    }
    return publicRoots.stream().flatMap(pr -> pr.getAccessPoints().stream())
        .map(ap -> Producer.builder().addr(ap.getAddress()).build())
        .toList();

  }

}
