from fractions import Fraction

NBANIMALS=4
NBICE=6

NBANISZ=10**len(str(NBANIMALS))#number to shift the igloo and bridge values

class NodeProba:
    """
    Class storing the probability of a game tree node
    """

    def __init__(self,win=0,loose=0):
        self.win = Fraction(win)
        self.loose = Fraction(loose)
    
    def __add__(self,other):
        return NodeProba(win=self.win+other.win,loose=self.loose+other.loose)

    def __iadd__(self,other):
        return self.__add__(other)

    def __repr__(self):
        return "(win={}={} loose={}={})".format(self.win,float(self.win),self.loose,float(self.loose))

    def __eq__(self,other):
        if self is not None and other is not None and self.win == other.win and self.loose==other.loose:
            return True
        else:
            return False

    def getChancesToWin(self):
        return self.win / ( self.win + self.loose)

class NodesStats:
    """
    Class storing globally the probabilities of already computed game tree nodes (to be able to compute probabilities of nodes with more than one infinite branch by using prevously computed probabilities of nodes with only one infinite branch)
    """
    
    instance = None # the instance of the singleton
    
    def __init__(self):
        self.stats = dict() # dict of proba with NodeState as key
   
    def isKnown(self,state):
        return state in self.stats
        
    def register(self,node):
        self.stats[node.state] = node.proba

    def getProba(self,node):
        if node.state in self.stats:
            return self.stats[node.state]
        else:
            return None
    
    @staticmethod  
    def getInstance():
        if NodesStats.instance == None:
            NodesStats.instance = NodesStats()
        return NodesStats.instance

class NodeState:
    """
    Class storing the state of the game, i.e. all game pawns positions of an on-going game.
    For this game the state is quite simple : it is the number of remaining ice pillars under the bridge, the number of animals which have reached the final igloo, and the number of animals on the bridge.
    The number of animals still at the start is not stored because it is computable from the total number of animals in the game, minus the numbet at the igloo and the number on the bridge
    """
    
    def __init__(self,iceOrOther,igloo=None,bridge=None):
        # check if copy constructor
        if isinstance(iceOrOther,NodeState):
            # copy constructor
            self.ice = iceOrOther.ice
            self.igloo = iceOrOther.igloo
            self.bridge = iceOrOther.bridge
        else:
            # Not copy constructor
            # Compare to 0 to allow safe use of -1 on this value in constructor'
            if iceOrOther > 0:
                self.ice=iceOrOther
            else:
                self.ice=0
            self.igloo=igloo
            if bridge > 0:
                self.bridge=bridge
            else:
                self.bridge=0
           
    def __eq__(self,other):
        if self.ice == other.ice and self.igloo==other.igloo and self.bridge==other.bridge:
            return True
        else:
            return False
            
    def __hash__(self):
        # to make this class usable as key dict
        # return an integer representing the object and allowing differenciating two of them
        return self.ice*NBANISZ*2+self.igloo*NBANISZ+self.bridge
        
    def __repr__(self):
        return "({} {} {})".format(self.ice,self.igloo,self.bridge)

class Node:
    """
    Class storing the data of a game node : the game state, the probability of its children related to it, and the links to its children nodes (possible outcomes of the next dice roll)
    """
    
    def __init__(self,state,depth,parent=None):
        self.state = state # NodeState type
        self.leaf = self.isLeaf()
        self.parent = parent # parenr Node, for debug purpose only
        self.depth = depth # depth from tree root,  for debug purpose only
        self.iceChild = None # Node type child
        self.iglooChild = None # Node type child
        self.bridgeChild = None # Node type child
        self.proba = None # NodeProba type
        # Check if this Node is a loose leaf
        if self.state.ice == 0:
            self.proba = NodeProba(loose=1)
        # Check if this Node is a win leaf
        if self.state.igloo == NBANIMALS:
            self.proba = NodeProba(win=1)
        # register Node at global level
        NodesStats.getInstance().register(self)
        #print("Create Node of state {} at depth {} with parent {}".format(self.state,self.depth,self.parent))# for debug purpose
        
    def generateChildren(self):
        if not self.leaf:
            # Ice dice roll
            self.iceChild=Node(state=NodeState(self.state.ice-1,self.state.igloo,self.state.bridge),depth=self.depth+1,parent=self)
            # Igloo dice roll
            if self.state.bridge != 0:
                igloo = self.state.igloo+1
                bridge = self.state.bridge-1
            else:
                igloo=self.state.igloo
                bridge=self.state.bridge
            self.iglooChild=Node(state=NodeState(self.state.ice,igloo,bridge),depth=self.depth+1,parent=self)
            # Bridge dice roll
            if (self.state.igloo+self.state.bridge) < NBANIMALS:
                bridge=self.state.bridge+1
            else:
                bridge=self.state.bridge
            self.bridgeChild=Node(state=NodeState(self.state.ice,self.state.igloo,bridge),depth=self.depth+1,parent=self)
        
    def children(self):
        if not self.leaf:
            return [self.iceChild,self.iglooChild,self.bridgeChild]
        else:
            return []
    
    def __repr__(self):
        return "State {} depth {}".format(self.state,self.depth)

    def isLeaf(self):
        leaf = False
        # Winning or loosing node
        if self.state.igloo == NBANIMALS or self.state.ice == 0:
            leaf = True
        # known node, no need to analyse its children
        if NodesStats.getInstance().isKnown(self.state):
            leaf = True
        return leaf

    def computeProba(self):
        # Check if the proba has been found elsewhere
        self.proba = NodesStats.getInstance().getProba(self)
        if self.proba is None:
            if len(self.children()) > 0:
                # Check if we are in the case of one infinite branch for a child
                nbInfinite = 0
                nbKnownProba = 0
                childrenProba = NodeProba()
                for child in self.children():
                    if child.proba is not None:
                        nbKnownProba += 1
                        childrenProba += NodeProba(win=child.proba.win/3,loose=child.proba.loose/3)
                    else:
                        if child.state == self.state:
                            nbInfinite += 1
                if nbKnownProba == 2 and nbInfinite == 1:
                    # In this case there is only one infinite branch with computable limit
                    self.proba = childrenProba + NodeProba(win=childrenProba.win/2,loose=childrenProba.loose/2)
                    # register Node Proba
                    NodesStats.getInstance().register(self)
                if nbKnownProba == 3:
                    # In this case the probability of all children has been computed, so simply use their computed sum
                    self.proba = childrenProba
                    # register Node Proba
                    NodesStats.getInstance().register(self)
                # else the proba is not computable
        #print("proba of {} depth {} parent {} computed : {}".format(self,self.depth, self.parent,self.proba))

        
def generateTree(node):
    # Generate the tree of all games except the repeated game states
    node.generateChildren()
    for child in node.children():
        generateTree(child)

def computeTreeProba(node):
    # Compute the probabilities of game states when possible and check whether new probabilities have been computed
    probaUpdated = False
    oldProba = node.proba
    node.computeProba()
    if oldProba != node.proba:
        probaUpdated = True
    for child in node.children():
        oldProba = child.proba
        childProbaUpdated = computeTreeProba(child)
        if oldProba != child.proba:
            probaUpdated = True
        if childProbaUpdated == True:
            probaUpdated = True
    return probaUpdated

if  __name__ == '__main__':
    # Creates roor node containing game start state
    root = Node(NodeState(iceOrOther=NBICE,igloo=0,bridge=0),depth=0)
    # generate tree of all possible games (without duplicated states)
    generateTree(root)

    # try computing probabilities of all game states
    while computeTreeProba(root):
        #print("Performe another loop of proba computing")
        pass

    # Print results
    print("Game root proba with {} animals and {} ice : {} sum win+loose={}".format(NBANIMALS,NBICE,root.proba,root.proba.win+root.proba.loose))
    if root.proba is not None:
        proba = root.proba.getChancesToWin()
        print("Game root chances to win with {} animals and {} ice : {}={}".format(NBANIMALS,NBICE,proba,float(proba)))

